"""
ingest/workers/pii_redactor.py
Hardened PII Redaction Gate for EPFO Statutory Rules & Cases System (Stage 3).
Strips all Indian personally identifiable information (PII) before documents,
orders, or community WhatsApp feeds enter raw_documents, vector stores, or LLM prompts.
"""

import re
from typing import Dict, Tuple


# Pre-compiled high-performance regular expressions for Indian statutory data
RE_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
RE_AADHAAR = re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b|\b(?<!\d)\d{12}(?!\d)\b")
RE_UAN = re.compile(r"\b10\d{10}\b|\b1[1-9]\d{10}\b")  # Standard 12-digit Indian UAN
RE_PHONE = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b")
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
RE_ESTABLISHMENT_CODE = re.compile(r"\b[A-Z]{2}[A-Z]{3}\d{7}\d{3}\b")  # Region (2) + Sub-region (3) + 7 digits + 3 digits extension

# Party name pattern for e-Proceedings & CGIT orders
RE_PARTY_PREFIX = re.compile(
    r"\b(?:M/s\.?|Shri\.?|Smt\.?|Mr\.?|Mrs\.?|Ms\.?)\s+"
    r"(?:(?!vs\b|versus\b|petitioner\b|respondent\b|appellant\b)[A-Z0-9][a-zA-Z0-9&\'\-]*\s*)+?"
    r"(?=[,\.\n;:]|\s+(?:vs\.?|versus|and\s+others|petitioner|respondent|appellant|\n|$))",
    re.IGNORECASE
)


class PIIRedactor:
    """
    Automated PII scrubbing engine.
    Produces clean redacted_text and a redaction audit summary.
    """

    @classmethod
    def redact(cls, text: str) -> Tuple[str, Dict[str, int]]:
        if not text:
            return "", {}

        counts = {
            "pan": 0,
            "aadhaar": 0,
            "uan": 0,
            "phone": 0,
            "email": 0,
            "establishment_code": 0,
            "party_names": 0,
        }

        # 1. Redact PAN
        def _pan_sub(m):
            counts["pan"] += 1
            return "[REDACTED_PAN]"
        cleaned = RE_PAN.sub(_pan_sub, text)

        # 2. Redact Email
        def _email_sub(m):
            counts["email"] += 1
            return "[REDACTED_EMAIL]"
        cleaned = RE_EMAIL.sub(_email_sub, cleaned)

        # 3. Redact Phone
        def _phone_sub(m):
            counts["phone"] += 1
            return "[REDACTED_PHONE]"
        cleaned = RE_PHONE.sub(_phone_sub, cleaned)

        # 4. Redact UAN (before generic Aadhaar 12-digit)
        def _uan_sub(m):
            counts["uan"] += 1
            return "[REDACTED_UAN]"
        cleaned = RE_UAN.sub(_uan_sub, cleaned)

        # 5. Redact Aadhaar
        def _aadhaar_sub(m):
            counts["aadhaar"] += 1
            return "[REDACTED_AADHAAR]"
        cleaned = RE_AADHAAR.sub(_aadhaar_sub, cleaned)

        # 6. Redact Establishment Code
        def _est_sub(m):
            counts["establishment_code"] += 1
            return "[REDACTED_EST_CODE]"
        cleaned = RE_ESTABLISHMENT_CODE.sub(_est_sub, cleaned)

        # 7. Redact Party Names in Quasi-Judicial Orders
        def _party_sub(m):
            counts["party_names"] += 1
            return "[REDACTED_PARTY]"
        cleaned = RE_PARTY_PREFIX.sub(_party_sub, cleaned)

        return cleaned, counts
