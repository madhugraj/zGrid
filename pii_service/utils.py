from typing import List, Dict, Any

GENERIC_PREFACE = {
    "email","e-mail","mail","phone","tel","telephone","mobile","mob","address","addr",
    "name","location","loc","city","state","country","contact","contacts","contact:"
}

def is_generic_preface_span(span_text: str) -> bool:
    t = (span_text or "").strip().lower()
    return t in GENERIC_PREFACE

def to_entity_dict(entity_type: str, value: str, start: int, end: int, score: float, replacement: str):
    return {
        "type": entity_type,
        "value": value,
        "start": int(start),
        "end": int(end),
        "score": round(float(score or 0.0), 6),
        "replacement": replacement,
    }

def apply_redactions(text: str, spans: List[Dict[str, Any]]) -> str:
    if not spans: 
        return text
    spans = sorted(spans, key=lambda x: x["start"])
    out, i = [], 0
    for s in spans:
        out.append(text[i:s["start"]])
        out.append(s.get("replacement", "[REDACTED]"))
        i = s["end"]
    out.append(text[i:])
    return "".join(out)

def merge_spans(text, presidio_spans, gliner_spans):
    """
    Merge with precedence:
      1) Keep Presidio spans (structured PII) if they overlap GLiNER.
      2) Between GLiNER spans, keep the longer / higher-score one.
    """
    for s in presidio_spans: s["_src"] = "presidio"
    for s in gliner_spans:   s["_src"] = "gliner"

    spans = presidio_spans + gliner_spans
    spans.sort(key=lambda s: (s["start"], -s["end"]))
    merged = []

    for s in spans:
        if not merged:
            merged.append(s); continue
        last = merged[-1]
        overlap = s["start"] < last["end"] and s["end"] > last["start"]
        if not overlap:
            merged.append(s); continue

        # conflict resolution
        if last["_src"] == "presidio" and s["_src"] == "gliner":
            continue  # keep presidio
        if last["_src"] == "gliner" and s["_src"] == "presidio":
            merged[-1] = s; continue

        # gliner vs gliner → longer or higher score
        last_len = last["end"] - last["start"]
        cur_len  = s["end"] - s["start"]
        if cur_len > last_len or (cur_len == last_len and s.get("score",0) > last.get("score",0)):
            merged[-1] = s

    for s in merged: s.pop("_src", None)
    return merged
