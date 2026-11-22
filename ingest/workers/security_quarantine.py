"""
ingest/workers/security_quarantine.py
Security Quarantine & URL Allowlister for EPFO Ingestion Pipeline (Stage 3).
Enforces strict origin boundaries (.gov.in / .nic.in only for PDFs)
and sanitizes untrusted Tier 4 community feeds against prompt injection.
"""

import re
from typing import Tuple
from urllib.parse import urlparse


# Sanctioned top-level official government domains for automated PDF download
OFFICIAL_GOV_DOMAINS = {
    "gov.in",
    "nic.in",
    "epfindia.gov.in",
    "egazette.gov.in",
    "pib.gov.in",
    "cgit.gov.in",
    "epfigms.gov.in",
    "delhihighcourt.nic.in",
    "main.sci.gov.in",
    "judgments.ecourts.gov.in",
}

# Prompt injection patterns in community WhatsApp/Reddit feeds
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"system\s*:\s*override", re.IGNORECASE),
    re.compile(r"<script[\s\S]*?>[\s\S]*?</script>", re.IGNORECASE),
    re.compile(r"DROP\s+TABLE|SELECT\s+\*\s+FROM|UNION\s+ALL\s+SELECT", re.IGNORECASE),
]


class SecurityQuarantine:
    """
    Validates target URLs and sanitizes untrusted incoming content.
    """

    @classmethod
    def validate_download_url(cls, url: str) -> Tuple[bool, str]:
        """
        Validates that PDF/document download targets originate from sanctioned .gov.in / .nic.in origins.
        """
        if not url:
            return False, "EMPTY_URL"

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()

        if not hostname:
            return False, "INVALID_HOSTNAME"

        # Check if domain or its parent domain ends with sanctioned domains
        is_allowed = any(
            hostname == d or hostname.endswith("." + d)
            for d in OFFICIAL_GOV_DOMAINS
        )

        if not is_allowed:
            return False, f"UNTRUSTED_DOMAIN_QUARANTINE: Host '{hostname}' is not in .gov.in/.nic.in allowlist."

        return True, "ALLOWED"

    @classmethod
    def sanitize_untrusted_text(cls, text: str) -> Tuple[str, bool]:
        """
        Sanitizes Tier 4 community feeds, WhatsApp posts, and user submissions
        against prompt injection attacks and malicious control tokens.
        """
        if not text:
            return "", False

        injection_detected = False
        cleaned = text

        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(cleaned):
                injection_detected = True
                cleaned = pattern.sub("[SANITIZED_INJECTION_ATTEMPT]", cleaned)

        # Strip null bytes and non-printable control characters
        cleaned = "".join(c for c in cleaned if c == "\n" or c == "\t" or (ord(c) >= 32 and ord(c) != 127))

        return cleaned, injection_detected
