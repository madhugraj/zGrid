from __future__ import annotations
import os, json
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from tox_model import ToxicityModel
from profanity import detect_and_apply
from utils import sentences_with_offsets, join_preserving_spacing, redact_ranges

# Load .env from this folder
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

app = FastAPI(title="Toxicity & Profanity Service", version="1.0.0")

# ------------- CORS -------------
ALLOWED = os.getenv("CORS_ALLOWED_ORIGINS", "*")
allow_origins = [o.strip() for o in ALLOWED.split(",")] if ALLOWED else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["POST","GET","OPTIONS"],
    allow_headers=["*"],
)

# ------------- API Keys -------------
_API_KEYS = set(k.strip() for k in (os.getenv("TOX_API_KEYS","")).split(",") if k.strip())
def require_api_key(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
):
    if not _API_KEYS:
        return
    token = x_api_key
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token or token not in _API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ------------- Defaults -------------
DEFAULT_MODEL = os.getenv("DETOXIFY_MODEL", "original").strip().lower()
DEFAULT_MODE = os.getenv("TOX_MODE", "sentence").strip().lower()
DEFAULT_ACTION = os.getenv("ACTION_ON_FAIL","remove_sentences").strip().lower()
DEFAULT_THRESHOLD = float(os.getenv("DETOXIFY_THRESHOLD","0.5"))
DEFAULT_LABELS = [s.strip() for s in os.getenv("DETOXIFY_LABELS","").split(",") if s.strip()]

PROF_ENABLED = os.getenv("PROFANITY_ENABLED","1") in ("1","true","True")
PROF_ACTION = os.getenv("PROFANITY_ACTION","mask").strip().lower()

# ------------- Schemas -------------
class ValidateRequest(BaseModel):
    text: str
    mode: Optional[str] = None                     # sentence | text
    tox_threshold: Optional[float] = None
    labels: Optional[List[str]] = None             # subset
    action_on_fail: Optional[str] = None           # remove_sentences | remove_all | redact
    profanity_enabled: Optional[bool] = None
    profanity_action: Optional[str] = None         # mask | remove
    return_spans: Optional[bool] = True

class Flagged(BaseModel):
    type: str
    score: float
    span: Optional[List[int]] = None
    sentence: Optional[str] = None
    token: Optional[str] = None                    # for profanity

class ValidateResponse(BaseModel):
    status: str                                    # pass | fixed
    clean_text: str
    flagged: List[Flagged]
    scores: Dict[str,float]                        # aggregate (max per label)
    steps: List[Dict[str, Any]]
    reasons: List[str]

# ------------- Model -------------
tox_model = ToxicityModel()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/validate", response_model=ValidateResponse, dependencies=[Depends(require_api_key)])
def validate(req: ValidateRequest):
    text = req.text or ""
    if not text.strip():
        return {
            "status": "pass",
            "clean_text": text,
            "flagged": [],
            "scores": {},
            "steps": [{"name":"noop","passed":True}],
            "reasons": ["Empty text"],
        }

    mode = (req.mode or DEFAULT_MODE).lower()
    threshold = float(req.tox_threshold if req.tox_threshold is not None else DEFAULT_THRESHOLD)
    labels = [l.strip().lower() for l in (req.labels or DEFAULT_LABELS or
              ["toxicity","severe_toxicity","obscene","threat","insult","identity_attack","sexual_explicit"])]
    action = (req.action_on_fail or DEFAULT_ACTION).lower()
    profanity_enabled = PROF_ENABLED if req.profanity_enabled is None else bool(req.profanity_enabled)
    profanity_action = (req.profanity_action or PROF_ACTION).lower()

    flagged: List[Dict[str,Any]] = []
    aggregate_scores: Dict[str,float] = {lab:0.0 for lab in labels}

    keep_ranges: List[tuple] = []
    bad_ranges: List[tuple] = []

    steps = []

    if mode == "text":
        scores_list = tox_model.score([text])
        scores = {k.lower(): float(v) for k,v in scores_list[0].items() if k.lower() in set(labels)}
        for k,v in scores.items():
            aggregate_scores[k] = max(aggregate_scores.get(k,0.0), v)
        breached = any(scores[k] >= threshold for k in labels if k in scores)

        if breached:
            # one toxic chunk: whole text is considered bad
            bad_ranges.append((0, len(text)))
            flagged.append({"type":"toxicity", "score": max(scores.values()), "span":[0, len(text)], "sentence": text})
        else:
            keep_ranges.append((0, len(text)))

    else:  # sentence mode
        sents = sentences_with_offsets(text)
        if not sents:
            sents = [(0, len(text), text)]
        sent_texts = [s[2] for s in sents]
        scores_list = tox_model.score(sent_texts)
        for idx, (start, end, stext) in enumerate(sents):
            scores = {k.lower(): float(v) for k,v in scores_list[idx].items() if k.lower() in set(labels)}
            for k,v in scores.items():
                if v > aggregate_scores.get(k,0.0):
                    aggregate_scores[k] = v
            breach = any(scores.get(k,0.0) >= threshold for k in labels)
            if breach:
                bad_ranges.append((start, end))
                flagged.append({"type":"toxicity", "score": max(scores.values()) if scores else 0.0,
                                "span":[start,end], "sentence": stext})
            else:
                keep_ranges.append((start, end))

    # Apply action for toxicity
    changed = False
    if bad_ranges:
        changed = True
        if action == "remove_all":
            out_text = ""
        elif action == "redact":
            out_text = redact_ranges(text, bad_ranges, token="[TOXIC]")
        else:  # remove_sentences (default)
            out_text = join_preserving_spacing(text, keep_ranges)
    else:
        out_text = text

    steps.append({"name": "detoxify", "passed": True, "details": {
        "mode": mode, "threshold": threshold, "labels": labels, "toxic_spans": len(bad_ranges)}})

    # Profanity pass (after toxicity action)
    prof_spans = []
    if profanity_enabled and out_text:
        out2, spans = detect_and_apply(out_text, action=profanity_action)
        if spans:
            changed = True
            prof_spans = [{"type":"profanity", "token": s["token"], "score": 1.0,
                           "span":[s["start"], s["end"]]} for s in spans]
        out_text = out2
        steps.append({"name":"profanity", "passed": True, "details": {"hits": len(spans), "action": profanity_action}})
    else:
        steps.append({"name":"profanity", "passed": True, "details": {"hits": 0, "action": profanity_action}})

    reasons = []
    if bad_ranges:
        if action == "remove_all":
            reasons.append("Toxic content removed (entire text).")
        elif action == "redact":
            reasons.append("Toxic sentences redacted.")
        else:
            reasons.append("Toxic sentences removed.")
    if prof_spans:
        if profanity_action == "remove":
            reasons.append(f"{len(prof_spans)} profanities removed.")
        else:
            reasons.append(f"{len(prof_spans)} profanities masked.")

    status = "fixed" if changed else "pass"
    return {
        "status": status,
        "clean_text": out_text,
        "flagged": flagged + prof_spans,
        "scores": aggregate_scores,
        "steps": steps,
        "reasons": reasons or (["No toxicity or profanity detected"] if not changed else []),
    }
