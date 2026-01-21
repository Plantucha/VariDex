#!/usr/bin/env python3
"""Text processing utilities for ACMG classifier."""

from typing import Optional, List
from functools import lru_cache
import pandas as pd

@lru_cache(maxsize=1024)
def normalize_text(text: Optional[str]) -> str:
    """Normalize text for consistent matching (cached)."""
    if pd.isna(text) or not text:
        return ""
    return str(text).strip().lower()

def split_delimited_value(value: str, delimiters: str = ",;") -> List[str]:
    """Split string on multiple delimiters and spaces."""
    if not value:
        return []
    normalized = value
    for delim in delimiters:
        normalized = normalized.replace(delim, ',')
    parts = [p.strip() for p in normalized.split(',')]
    return [p for p in parts if p]
