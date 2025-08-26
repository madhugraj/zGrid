import os, json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env next to this file
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

from .pii_gliner import GlinerDetector
from .pii_presidio import analyze_presidio, anonymize_presidio
from .utils import to_entity_dict, merge_spans, apply_redactions, is_generic_preface_span

app = FastAPI(title="PII Protection Service", version="1.1.0")

# Defaults from env
LANG = os.getenv("PRESIDIO_LANGUAGE", "en")
DEFAULT_ENTITIES = [s.strip() for s in os.getenv("ENTITIES", "").split(",") if s.strip()]
ENTITY_THRESHOLDS = json.loads(os.getenv("ENTITY_THRESHOLDS", "{}") or "{}")
PLACEHOLDERS = json.loads(os.getenv("PLACEHOLDERS", '{"DEFAULT":"[REDACTED]"}') or '{"DEFAULT":"[REDACTED]"}')

# Map PII types to GLiNER labels (semantic only)
GLINER_LABEL_MAP = {
    "PERSON": "person",
    "LOCATION": "location",
    "ORGANIZATION": "organization",
}

gliner = GlinerDetector()

class ValidateRequest(BaseModel):
    text: str
    entities: Optional[List[str]] = None
    gliner_labels: Optional[List[str]] = None
    gliner_threshold: Optional[float] = None
    thresholds: Optional[Dict[str, float]] = None
    return_spans: Optional[bool] = True
    language: Optional[str] = None

class EntityOut(BaseModel):
    type: str
    value: str
    start: int
    end: int
    score: float
    replacement: str

class ValidateResponse(BaseModel):
    status: str
    redacted_text: str
    entities: List[EntityOut]
    steps: List[Dict[str, Any]]
    reasons: List[str]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest):
    text = req.text or ""
    if not text.strip():
        return {
            "status": "pass",
            "redacted_text": text,
            "entities": [],
            "steps": [{"name":"noop","passed":True}],
            "reasons": ["Empty text"],
        }

    language = req.language or LANG
    entities = req.entities or DEFAULT_ENTITIES or [
        # sensible broad default if ENTITIES not set
        "EMAIL_ADDRESS","PHONE_NUMBER","CREDIT_CARD","US_SSN","US_PASSPORT","IP_ADDRESS",
        "IBAN_CODE","PERSON","LOCATION","ORGANIZATION","IN_AADHAAR","IN_PAN","IN_PASSPORT"
    ]
    thresholds = {**ENTITY_THRESHOLDS, **(req.thresholds or {})}
    global_th = min(thresholds.values()) if thresholds else 0.30

    # ---------- Presidio ----------
    pres_results = analyze_presidio(
        text=text,
        language=language,
        entities=entities,
        global_threshold=global_th,
        per_entity_threshold=thresholds
    )
    presidio_spans = []
    for r in pres_results:
        repl = PLACEHOLDERS.get(r.entity_type, PLACEHOLDERS.get("DEFAULT", "[REDACTED]"))
        presidio_spans.append(to_entity_dict(
            entity_type=r.entity_type,
            value=text[r.start:r.end],
            start=r.start,
            end=r.end,
            score=float(r.score or 0.0),
            replacement=repl
        ))

    # ---------- GLiNER (semantic NER) ----------
    wanted_labels = req.gliner_labels or list({GLINER_LABEL_MAP.get(e) for e in entities if GLINER_LABEL_MAP.get(e)})
    wanted_labels = [w for w in wanted_labels if w]
    gl_thr = req.gliner_threshold if req.gliner_threshold is not None else None

    gliner_spans = []
    if wanted_labels:
        preds = gliner.detect(text, labels=wanted_labels, threshold=gl_thr)
        for p in preds:
            raw = text[p["start"]:p["end"]]
            if is_generic_preface_span(raw):
                continue
            label_upper = (p.get("label") or "").upper()
            if "PERSON" in label_upper:
                pii_type = "PERSON"
            elif "LOC" in label_upper:
                pii_type = "LOCATION"
            elif "ORG" in label_upper:
                pii_type = "ORGANIZATION"
            else:
                pii_type = label_upper or "PERSON"
            # minimum length heuristic for names/orgs to reduce FPs
            if pii_type in ("PERSON","ORGANIZATION") and len(raw.strip()) < 2:
                continue
            repl = PLACEHOLDERS.get(pii_type, PLACEHOLDERS.get("DEFAULT", "[REDACTED]"))
            gliner_spans.append(to_entity_dict(
                entity_type=pii_type,
                value=raw,
                start=int(p["start"]),
                end=int(p["end"]),
                score=float(p.get("score", 0.0)),
                replacement=repl
            ))

    steps = [
        {"name": "presidio", "passed": True, "details": {"count": len(presidio_spans)}},
        {"name": "gliner", "passed": True, "details": {"count": len(gliner_spans), "labels": wanted_labels}},
    ]

    # ---------- Merge + redact ----------
    merged = merge_spans(text, presidio_spans, gliner_spans)
    if not merged:
        return {
            "status": "pass",
            "redacted_text": text,
            "entities": [],
            "steps": steps,
            "reasons": ["No PII detected"],
        }

    redacted = apply_redactions(text, merged)
    return {
        "status": "fixed",
        "redacted_text": redacted,
        "entities": merged if (req.return_spans is None or req.return_spans) else [],
        "steps": steps,
        "reasons": ["PII redacted"],
    }
