from __future__ import annotations
import os
from typing import List, Dict, Any, Tuple
import nltk
from nltk.tokenize import sent_tokenize
import re

# Download required NLTK data on first import
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

def sentences_with_offsets(text: str) -> List[Tuple[int,int,str]]:
    """Return list of (start, end, sentence_text)."""
    if not text.strip():
        return []
    
    # Use NLTK for sentence tokenization
    sentences = sent_tokenize(text)
    out = []
    current_pos = 0
    
    for sentence in sentences:
        # Find the sentence in the original text starting from current position
        start = text.find(sentence, current_pos)
        if start == -1:
            # Fallback: use regex to find sentence boundaries
            start = current_pos
        end = start + len(sentence)
        out.append((start, end, sentence))
        current_pos = end
    
    if not out:  # fallback if no sentences found
        out = [(0, len(text), text)]
    return out

def join_preserving_spacing(text: str, keep_ranges: List[Tuple[int,int]]) -> str:
    """Join segments of original text given by keep_ranges."""
    pieces = [text[s:e] for (s,e) in keep_ranges]
    # naive join preserves exact substrings; add single spaces if needed
    out = "".join(pieces)
    # normalize multiple spaces
    return " ".join(out.split())

def redact_ranges(text: str, bad_ranges: List[Tuple[int,int]], token: str="[TOXIC]") -> str:
    """Replace bad ranges with a token; keep other text unchanged."""
    if not bad_ranges:
        return text
    bad_ranges = sorted(bad_ranges, key=lambda x: x[0])
    out, i = [], 0
    for s,e in bad_ranges:
        s = max(0, min(len(text), s))
        e = max(0, min(len(text), e))
        if s < i:  # overlapping; skip
            continue
        out.append(text[i:s])
        out.append(token)
        i = e
    out.append(text[i:])
    return "".join(out)
