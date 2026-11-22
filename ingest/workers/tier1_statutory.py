"""
ingest/workers/tier1_statutory.py
Tier 1 Ingestion Worker: e-Gazette, EPFO Circulars & Official Manuals.
Implements:
- 5-minute conditional HTTP probes (304 Not Modified skip)
- Security quarantine verification (.gov.in/.nic.in allowlist)
- PII redaction gate
- Corrigendum auto-pairing
- Candidate diff extraction for Stage 4 gate
"""

import hashlib
from typing import Any, Dict, List, Optional
from ingest.workers.pii_redactor import PIIRedactor
from ingest.workers.security_quarantine import SecurityQuarantine
from ingest.workers.corrigendum_matcher import CorrigendumMatcher
from ingest.workers.diff_extractor import SandboxedDiffExtractor, CandidateDiff


class Tier1StatutoryWorker:
    """
    Ingestion engine for Tier 1 official sources.
    """

    def __init__(self, etag_cache: Optional[Dict[str, str]] = None):
        self.etag_cache: Dict[str, str] = etag_cache or {}
        self.quarantine_violations: List[str] = []

    def probe_conditional_headers(self, url: str, server_etag: Optional[str] = None) -> bool:
        """
        Simulates 5-minute conditional HTTP probe (ETag / If-Modified-Since).
        Returns True if modified (200 OK), False if unchanged (304 Not Modified).
        """
        cached_etag = self.etag_cache.get(url)
        if server_etag and cached_etag == server_etag:
            # 304 Not Modified
            return False

        if server_etag:
            self.etag_cache[url] = server_etag
        return True

    def process_document(
        self,
        raw_text: str,
        citation_url: str,
        published_at: Optional[str] = None,
        language: str = "en",
        source_id: str = "tier1_epfo_circulars",
    ) -> Dict[str, Any]:
        """
        Executes complete Tier 1 processing pipeline:
        1. Security Quarantine check on URL
        2. Cryptographic SHA-256 fingerprinting
        3. Automated PII scrubbing
        4. Corrigendum & supersession detection
        5. Candidate diff generation
        """
        # 1. Security Quarantine Gate
        allowed, reason = SecurityQuarantine.validate_download_url(citation_url)
        if not allowed:
            self.quarantine_violations.append(f"{citation_url}: {reason}")
            raise PermissionError(f"Security Quarantine Reject: {reason}")

        # 2. SHA-256 Computation
        doc_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        # 3. PII Redaction
        redacted_text, pii_summary = PIIRedactor.redact(raw_text)

        # 4. Corrigendum & Supersession Detection
        is_mod, rel_type, ref_no = CorrigendumMatcher.detect_supersession(redacted_text)
        doc_group_id = CorrigendumMatcher.generate_doc_group_id(ref_no) if ref_no else f"DOC_{doc_sha256[:12]}"

        # 5. Extract Candidate Diff if statutory rule update detected
        candidate_diff: Optional[CandidateDiff] = None
        if "wage ceiling" in redacted_text.lower() or "monthly wage" in redacted_text.lower():
            candidate_diff = SandboxedDiffExtractor.extract_wage_ceiling_candidate(
                text=redacted_text,
                doc_sha256=doc_sha256,
                citation_url=citation_url,
                precedence_rank=10,
            )

        return {
            "doc_sha256": doc_sha256,
            "citation_url": citation_url,
            "archive_uri": f"s3://epfo-documents/{doc_sha256[:4]}/{doc_sha256}.pdf",
            "doc_group_id": doc_group_id,
            "language": language,
            "redacted_text": redacted_text,
            "pii_redacted_count": sum(pii_summary.values()),
            "is_corrigendum": is_mod,
            "superseded_reference": ref_no,
            "candidate_diff": candidate_diff.to_dict() if candidate_diff else None,
            "source_id": source_id,
        }
