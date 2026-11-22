"""
ingest/workers/portal_ui_canary.py
Synthetic Portal UI Canary Worker for Unified Employer & Member Portals.
Diffs DOM dropdowns, form validation constraints, and error messages
to detect portal shifts before PDF manuals are officially published.
"""

import hashlib
from typing import Any, Dict, List, Optional, Tuple


class PortalUICanary:
    """
    Read-only synthetic probe for public & authenticated portal interfaces.
    """

    def __init__(self, last_dom_hash: Optional[str] = None):
        self.last_dom_hash = last_dom_hash

    def inspect_dom_state(self, form_code: str, dom_snippet: str) -> Dict[str, Any]:
        """
        Computes DOM hash and detects breaking validation shifts or new dropdown options.
        """
        current_hash = hashlib.sha256(dom_snippet.encode("utf-8")).hexdigest()
        is_changed = (self.last_dom_hash is not None and current_hash != self.last_dom_hash)
        self.last_dom_hash = current_hash

        detected_fields: List[str] = []
        if "data-lexical-editor" in dom_snippet or "contenteditable" in dom_snippet:
            detected_fields.append("RICH_TEXT_LEXICAL_CONTAINER")
        if "max-claim-amount" in dom_snippet or "claim_limit" in dom_snippet:
            detected_fields.append("CLAIM_CEILING_VALIDATOR")
        if "aadhaar_otp_required" in dom_snippet:
            detected_fields.append("MANDATORY_OTP_GATE")

        return {
            "form_code": form_code,
            "dom_hash": current_hash,
            "is_dom_changed": is_changed,
            "detected_validators": detected_fields,
            "requires_form_requirement_update": is_changed and bool(detected_fields),
        }
