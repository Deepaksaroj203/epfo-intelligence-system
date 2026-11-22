"""
ingest/workers/tier3_4_social_whatsapp.py
Tier 3 & 4 Ingestion Worker: Official Social Handles & Community Feeds.
Implements:
- Prompt injection sanitization for untrusted feeds
- PII redaction of WhatsApp phone numbers and user details
- Confidence scoring and 06:30 IST time decay for community workarounds
- Official @officialepfo verification tagging
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ingest.workers.pii_redactor import PIIRedactor
from ingest.workers.security_quarantine import SecurityQuarantine


class Tier34SocialWorker:
    """
    Ingests and normalizes community fixes into portal_troubleshooting_kb.
    """

    @classmethod
    def process_community_post(
        cls,
        raw_text: str,
        source_channel: str,  # "whatsapp", "reddit", "x_tag"
        error_code: str,
        portal_side: str = "member",
        is_verified_by_official: bool = False,
    ) -> Dict[str, Any]:
        # 1. Sanitize against prompt injection attacks
        sanitized_text, injection_detected = SecurityQuarantine.sanitize_untrusted_text(raw_text)

        # 2. PII Redaction (strip phone numbers from WhatsApp exports)
        redacted_text, pii_counts = PIIRedactor.redact(sanitized_text)

        # 3. Confidence Scoring
        # Official confirmation starts at 0.950; unverified community starts at 0.700
        if is_verified_by_official:
            confidence = 0.950
        elif source_channel == "x_tag":
            confidence = 0.800
        elif source_channel == "reddit":
            confidence = 0.750
        else:
            confidence = 0.700

        # Penalize if injection attempted
        if injection_detected:
            confidence = max(0.100, confidence - 0.400)

        return {
            "error_code": error_code,
            "portal_side": portal_side,
            "symptom": f"Reported issue from {source_channel}: {error_code}",
            "root_cause": "Community reported portal behavior / error code",
            "remediation_steps": {"steps": [redacted_text.strip()]},
            "confidence_score": confidence,
            "source_tier": 3 if is_verified_by_official else 4,
            "source_reference": source_channel,
            "verified_by_official": is_verified_by_official,
            "injection_detected": injection_detected,
            "pii_redacted": pii_counts,
        }

    @classmethod
    def apply_confidence_decay(cls, initial_score: float, days_unverified: int) -> float:
        """
        06:30 IST daily job: Decays confidence score of Tier 4 unverified community fixes
        by 0.01 per day if not confirmed by official circular or @officialepfo reply.
        """
        decay = 0.01 * days_unverified
        return max(0.200, round(initial_score - decay, 3))
