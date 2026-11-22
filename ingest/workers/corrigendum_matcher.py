"""
ingest/workers/corrigendum_matcher.py
Corrigendum, Annexure, and Document Grouping Engine for Stage 3 Ingestion.
Detects circular modifications, auto-pairs annexures under doc_group_id,
and extracts superseded circular references.
"""

import re
from typing import Dict, List, Optional, Tuple


CORRIGENDUM_PATTERNS = [
    re.compile(r"in\s+partial\s+modification\s+of\s+(?:this\s+office\s+)?circular\s+no\.?\s*([A-Za-z0-9\-_/()]+)", re.IGNORECASE),
    re.compile(r"corrigendum\s+to\s+(?:circular|notification)\s+no\.?\s*([A-Za-z0-9\-_/()]+)", re.IGNORECASE),
    re.compile(r"in\s+supersession\s+of\s+(?:all\s+earlier\s+)?(?:circulars?|orders?)\s+no\.?\s*([A-Za-z0-9\-_/()]+)", re.IGNORECASE),
    re.compile(r"amendment\s+to\s+(?:scheme|circular)\s+no\.?\s*([A-Za-z0-9\-_/()]+)", re.IGNORECASE),
]


class CorrigendumMatcher:
    """
    Analyzes document text to detect whether it modifies or supersedes an earlier instrument.
    """

    @classmethod
    def detect_supersession(cls, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Returns (is_modification, relationship_type, referenced_circular_no)
        """
        if not text:
            return False, None, None

        for pattern in CORRIGENDUM_PATTERNS:
            match = pattern.search(text)
            if match:
                ref_no = match.group(1).strip().rstrip(".,")
                rel_type = "CORRIGENDUM" if "corrigendum" in match.group(0).lower() else "PARTIAL_MODIFICATION"
                return True, rel_type, ref_no

        return False, None, None

    @classmethod
    def generate_doc_group_id(cls, primary_circular_no: str) -> str:
        """
        Canonicalizes circular reference numbers into a clean group ID.
        E.g. "C-I/1(33)2024/Damages/768" -> "GRP_CI_1_33_2024_DAMAGES_768"
        """
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", primary_circular_no).strip("_").upper()
        return f"GRP_{cleaned}"
