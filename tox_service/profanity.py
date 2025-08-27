from __future__ import annotations
import os, re
from typing import List, Dict, Any, Tuple
from better_profanity import profanity as _pf

_INIT = False

def _init_profane():
    global _INIT
    if _INIT: return
    # Load base dictionary
    _pf.load_censor_words()
    extra = os.getenv("PROFANITY_EXTRA_WORDS","").strip()
    if extra:
        words = [w.strip().lower() for w in extra.split(",") if w.strip()]
        _pf.add_censor_words(words)
    _INIT = True

def _censor(text: str, censor_char: str="*") -> str:
    # better_profanity uses * by default; we can set char as needed:
    return _pf.censor(text, censor_char=censor_char)

def detect_and_apply(text: str, action: str="mask") -> Tuple[str, List[Dict[str,Any]]]:
    """
    Return (clean_text, spans).
    - spans: [{token: str, start: int, end: int}]
    """
    _init_profane()
    censored = _censor(text, "*")
    if censored == text:
        return text, []
    # find changed regions
    spans = []
    i = 0
    while i < len(text):
        if text[i] != censored[i]:
            # start of a censored region
            j = i
            while j < len(text) and text[j] != censored[j]:
                j += 1
            spans.append({"token": text[i:j], "start": i, "end": j})
            i = j
        else:
            i += 1
    if action == "mask":
        return censored, spans
    elif action == "remove":
        # remove those spans entirely
        out, k = [], 0
        for s in spans:
            out.append(text[k:s["start"]])
            k = s["end"]
        out.append(text[k:])
        return "".join(out), spans
    else:
        return censored, spans
