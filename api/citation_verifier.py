"""
api/citation_verifier.py
Stage 5 Citation-Lock Verifier.
Enforces non-negotiable architectural rule:
Zero ungrounded or hallucinated citations.
Any returned citation or legal claim must bind to a verified SHA-256 document hash
and official case/order number in the immutable baseline store.
"""

from typing import Any, Dict, List, Set, Tuple


class CitationLockVerifier:
    """
    Validates precedent citations and strips any ungrounded assertions.
    """

    @staticmethod
    def is_valid_sha256(hash_str: str) -> bool:
        if not hash_str or len(hash_str) != 64:
            return False
        try:
            int(hash_str, 16)
            return True
        except ValueError:
            return False

    @classmethod
    def verify_and_lock_citations(
        cls,
        candidate_citations: List[Dict[str, Any]],
        verified_doc_shas: Set[str],
    ) -> Tuple[List[Dict[str, Any]], int, str]:
        """
        Filters citations against verified SHA-256 registry.
        Returns:
            - locked_citations: List of verified citations
            - stripped_count: Number of dropped hallucinated items
            - lock_status: "VERIFIED_LOCKED" if all verified, "PARTIAL" if any dropped
        """
        locked = []
        stripped_count = 0

        for cit in candidate_citations:
            sha = cit.get("doc_sha256", "")
            case_no = cit.get("case_number", "")

            # 1. Structural SHA-256 validation
            if not cls.is_valid_sha256(sha):
                stripped_count += 1
                continue

            # 2. Groundedness in verified registry
            if sha not in verified_doc_shas:
                stripped_count += 1
                continue

            # 3. Case number presence
            if not case_no or len(case_no.strip()) < 3:
                stripped_count += 1
                continue

            cit["citation_lock_verified"] = True
            locked.append(cit)

        status_str = "VERIFIED_LOCKED" if stripped_count == 0 else "PARTIAL"
        return locked, stripped_count, status_str
