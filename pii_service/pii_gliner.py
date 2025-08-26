import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from gliner import GLiNER

class GlinerDetector:
    def __init__(self):
        base = Path(__file__).parent
        local_dir = os.getenv("GLINER_LOCAL_DIR")
        if local_dir and not os.path.isabs(local_dir):
            local_dir = str((base / local_dir).resolve())

        model_id  = os.getenv("GLINER_MODEL", "urchade/gliner_small-v2.1")
        offline = os.getenv("HF_HUB_OFFLINE", "0").lower() in ("1","true","yes")

        if local_dir and Path(local_dir).is_dir():
            self.model = GLiNER.from_pretrained(local_dir)
        else:
            if offline:
                raise RuntimeError(
                    "HF_HUB_OFFLINE=1 but GLINER_LOCAL_DIR is invalid. "
                    "Set GLINER_LOCAL_DIR to a downloaded model directory."
                )
            self.model = GLiNER.from_pretrained(model_id)

        labels = os.getenv("GLINER_LABELS", "person,location,organization")
        self.labels = [s.strip() for s in labels.split(",") if s.strip()]
        self.threshold = float(os.getenv("GLINER_THRESHOLD", "0.60"))

    def detect(self, text: str, labels: Optional[List[str]] = None, threshold: Optional[float]=None) -> List[Dict[str, Any]]:
        lbls = labels or self.labels
        thr  = threshold if threshold is not None else self.threshold
        if not lbls or not text.strip():
            return []
        # returns [{start, end, label, score}]
        return self.model.predict_entities(text, labels=lbls, threshold=thr)
