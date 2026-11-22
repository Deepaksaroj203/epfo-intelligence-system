"""
ingest/workers/tier2_cases_courts.py
Tier 2 Ingestion Worker: PIB Releases, e-Proceedings & Judicial Orders.
Implements:
- CBT announcement tagging (announced_pending_gazette)
- High Court / Supreme Court stay detection (judicial_overrides)
- Quasi-judicial order PII scrubbing (party names, establishment codes)
- Section 7A, 14B & 7Q precedent indexing
"""

import hashlib
import re
from typing import Any, Dict, List, Optional
from ingest.workers.pii_redactor import PIIRedactor
from ingest.workers.security_quarantine import SecurityQuarantine


RE_COURT_STAY = re.compile(
    r"\b(?:stayed|quashed|interim\s+stay|granted\s+stay|operation\s+of\s+circular\s+stayed)\b",
    re.IGNORECASE
)
RE_CBT_APPROVAL = re.compile(
    r"\b(?:Central\s+Board\s+of\s+Trustees|CBT)\s+(?:approved|recommended|recommended\s+hike)\b",
    re.IGNORECASE
)


class Tier2CasesCourtsWorker:
    """
    Ingestion engine for Tier 2 case law, tribunal precedents, and court overrides.
    """

    def process_order(
        self,
        raw_text: str,
        case_citation: str,
        court_name: str,
        citation_url: str,
        jurisdiction_zone: str = "ALL",
        source_id: str = "tier2_cgit_tribunal",
    ) -> Dict[str, Any]:
        # Security quarantine check
        allowed, reason = SecurityQuarantine.validate_download_url(citation_url)
        if not allowed:
            raise PermissionError(f"Security Quarantine Reject: {reason}")

        # Compute SHA-256
        doc_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        # PII Scrubbing
        redacted_text, pii_summary = PIIRedactor.redact(raw_text)

        # Detect Court Stays / Overrides
        is_stay = bool(RE_COURT_STAY.search(redacted_text))
        is_cbt = bool(RE_CBT_APPROVAL.search(redacted_text))

        override_candidate = None
        if is_stay:
            override_candidate = {
                "target_table": "judicial_overrides",
                "case_citation": case_citation,
                "court_name": court_name,
                "jurisdiction_zone": jurisdiction_zone,
                "override_type": "stayed",
                "precedence_rank": 5,  # Top priority
                "order_summary": f"Court order staying enforcement: {case_citation} ({court_name})",
                "citation_url": citation_url,
                "doc_sha256": doc_sha256,
            }

        status_tag = "active"
        if is_cbt and not is_stay:
            status_tag = "announced_pending_gazette"

        return {
            "doc_sha256": doc_sha256,
            "case_citation": case_citation,
            "court_name": court_name,
            "citation_url": citation_url,
            "archive_uri": f"s3://epfo-documents/judiciary/{doc_sha256}.pdf",
            "redacted_text": redacted_text,
            "pii_redacted_count": sum(pii_summary.values()),
            "is_stay": is_stay,
            "is_cbt_announcement": is_cbt,
            "status_tag": status_tag,
            "override_candidate": override_candidate,
            "source_id": source_id,
        }
