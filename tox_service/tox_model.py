from __future__ import annotations
import os
from typing import List, Dict
from detoxify import Detoxify

_MODEL = None

class ToxicityModel:
    def __init__(self):
        global _MODEL
        if _MODEL is None:
            fam = os.getenv("DETOXIFY_MODEL", "original").strip().lower()
            if fam not in {"original","unbiased","multilingual"}:
                fam = "original"
            # This will load from cache if present; otherwise it will fetch once.
            # In production, warm the cache during build and set HF_HUB_OFFLINE=1.
            _MODEL = Detoxify(fam)
        self.model = _MODEL

    def score(self, texts: List[str]) -> List[Dict[str,float]]:
        """Return list of label->score dicts for each input text."""
        if not texts:
            return []
        # Detoxify accepts list and returns dict of lists.
        results = self.model.predict(texts)
        # results: {label: [scores...]}
        labels = list(results.keys())
        out: List[Dict[str,float]] = []
        for i in range(len(texts)):
            d = {lab: float(results[lab][i]) for lab in labels}
            out.append(d)
        return out
