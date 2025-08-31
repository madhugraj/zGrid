import os, re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# load .env when running locally
load_dotenv(Path(__file__).parent / ".env")

from llama_cpp import Llama

app = FastAPI(title="Policy Moderation (LlamaGuard-7B)", version="1.0.0")

allowed = [o.strip() for o in (os.getenv("CORS_ALLOWED_ORIGINS","")).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed or ["*"],
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

API_KEYS = [s.strip() for s in os.getenv("POLICY_API_KEYS","").split(",") if s.strip()]
MODEL_PATH = os.getenv("LLAMAGUARD_GGUF")
ACTION_DEFAULT = (os.getenv("POLICY_ACTION_ON_FAIL","refrain") or "refrain").lower()
N_THREADS = int(os.getenv("N_THREADS","0"))
N_CTX = int(os.getenv("N_CTX","2048"))

# Lightweight policy summary; can be externalized later if you want a file.
POLICY = """Task: classify if the text complies with the safety policy.
Return exactly one line: "SAFE" or "UNSAFE: <CATEGORY_LIST>".

Policy categories (examples, not exhaustive):
- HATE / HARASSMENT
- SEXUAL (incl. minors)
- VIOLENCE / WEAPONS
- SELF-HARM
- CRIME / ILLEGAL
- DRUGS
- FRAUD / PRIVACY / PI
- OTHER DANGEROUS CONTENT
"""

PROMPT_TMPL = """{policy}

[Text]
{content}

[Output]
"""

_llm: Optional[Llama] = None

def get_llm() -> Llama:
    global _llm
    if _llm is None:
        p = MODEL_PATH
        if not p:
            raise RuntimeError("LLAMAGUARD_GGUF not set")
        path = Path(p)
        if not path.exists():
            # also try relative to this file
            alt = Path(__file__).parent / p
            if not alt.exists():
                raise RuntimeError(f"Model path not found: {p}")
            path = alt
        _llm = Llama(
            model_path=str(path),
            n_ctx=N_CTX,
            n_threads=(None if N_THREADS <= 0 else N_THREADS),
            logits_all=False,
            embedding=False,
        )
    return _llm

class ValidateRequest(BaseModel):
    text: str
    action_on_fail: Optional[str] = None
    return_spans: Optional[bool] = True

class Flag(BaseModel):
    type: str
    score: float
    categories: Optional[List[str]] = None

class ValidateResponse(BaseModel):
    status: str
    clean_text: str
    flagged: List[Flag]
    steps: List[Dict]
    reasons: List[str]

def require_key(x_api_key: Optional[str]):
    if API_KEYS and (not x_api_key or x_api_key not in API_KEYS):
        raise HTTPException(status_code=401, detail="Unauthorized")

def parse_guard_output(txt: str) -> Tuple[bool, List[str]]:
    line0 = txt.strip().splitlines()[0].strip()
    if line0.upper().startswith("SAFE"):
        return False, []
    m = re.match(r"UNSAFE\s*:?\s*(.*)", line0, re.I)
    if m:
        cats = [c.strip() for c in re.split(r"[;,]", m.group(1)) if c.strip()]
        return True, (cats or ["UNSPECIFIED"])
    # conservative default
    return True, ["UNSPECIFIED"]

def apply_action(text: str, unsafe: bool, action: str) -> Tuple[str,str]:
    if not unsafe:
        return text, "Complies with policy"
    a = (action or ACTION_DEFAULT).lower()
    if a == "filter":
        return "[REQUEST REDACTED DUE TO SAFETY POLICY]", "Filtered"
    if a == "reask":
        return "I can’t help with that. Could you rephrase your request safely?", "Re-asked"
    return "", "Blocked"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest, x_api_key: Optional[str] = Header(default=None)):
    require_key(x_api_key)

    text = (req.text or "").strip()
    if not text:
        return {
            "status":"pass",
            "clean_text":"",
            "flagged":[],
            "steps":[{"name":"noop","passed":True}],
            "reasons":["Empty text"],
        }

    try:
        llm = get_llm()
        prompt = PROMPT_TMPL.format(policy=POLICY, content=text)
        out = llm(prompt, max_tokens=64, temperature=0.0, stop=["\n\n", "\n[", "\nUser:"])
        
        # Add validation for LLM response structure
        if not out or "choices" not in out or len(out["choices"]) == 0 or "text" not in out["choices"][0]:
            raise RuntimeError("LLM did not return expected response structure")
            
        raw = out["choices"][0]["text"]
        unsafe, cats = parse_guard_output(raw)

        flagged = [Flag(type="policy", score=1.0, categories=cats)] if unsafe else []
        steps = [{"name":"llamaguard","passed": not unsafe, "details":{"model":Path(MODEL_PATH).name if MODEL_PATH else "", "raw": raw.strip()[:200]}}]
        clean, reason = apply_action(text, unsafe, req.action_on_fail or ACTION_DEFAULT)
        status = "blocked" if unsafe and (req.action_on_fail or ACTION_DEFAULT)=="refrain" else ("fixed" if unsafe else "pass")

        return {"status": status, "clean_text": clean, "flagged": flagged, "steps": steps, "reasons": [reason]}
    except Exception as e:
        # Log the error and return a safe response
        print(f"Error in validation: {str(e)}")
        return {
            "status": "error",
            "clean_text": "",
            "flagged": [],
            "steps": [{"name": "error", "passed": False, "details": {"error": str(e)}}],
            "reasons": [f"Validation error: {str(e)}"]
        }
