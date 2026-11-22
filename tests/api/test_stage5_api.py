"""
tests/api/test_stage5_api.py
Stage 5 Production FastAPI Test Suite.
Verifies all 6 compliance endpoints, tenant authentication, citation-locking,
and seamless integration with Stage 1-4 deterministic engines and baseline.
"""

from datetime import date
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "test-api-key"}


# ============================================================================
# 1. SYSTEM HEALTH & INTEGRITY TESTS
# ============================================================================

def test_health_check_endpoint():
    """
    GET /health verifies active rules, hash-chain integrity, and pipeline status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["hash_chain_integrity"] is True
    assert data["active_rules_count"] >= 10
    assert "06:00_IST" in data["autonomous_pipeline"]


# ============================================================================
# 2. TENANT AUTHENTICATION & SECURITY GATE TESTS
# ============================================================================

def test_auth_rejection_on_missing_credentials():
    """
    Endpoints must reject unauthenticated requests with 401 Unauthorized.
    """
    response = client.get("/v1/rules/as-of?rule_key=statutory_wage_ceiling&event_date=2024-01-01")
    assert response.status_code == 401
    assert "Missing API authentication" in response.json()["detail"]


def test_auth_rejection_on_invalid_key():
    """
    Endpoints must reject forged or invalid API keys.
    """
    response = client.get(
        "/v1/rules/as-of?rule_key=statutory_wage_ceiling&event_date=2024-01-01",
        headers={"X-API-Key": "invalid-hacker-key"},
    )
    assert response.status_code == 401
    assert "Invalid X-API-Key" in response.json()["detail"]


def test_auth_success_with_bearer_jwt():
    """
    Valid Bearer JWT token passes authentication.
    """
    response = client.get(
        "/v1/rules/as-of?rule_key=statutory_wage_ceiling&event_date=2024-01-01",
        headers={"Authorization": "Bearer epfo-system-jwt"},
    )
    assert response.status_code == 200
    assert response.json()["value_numeric"] == 1500000


# ============================================================================
# 3. MEMBER EVALUATION ENDPOINT TESTS (POST /v1/member/evaluate)
# ============================================================================

def test_member_evaluate_successful_claim():
    """
    A member with complete service and KYC receives deterministic evaluation
    with integer-paise calculations, approval tier, and citation envelope.
    """
    payload = {
        "joining_date": "2020-01-01",
        "exit_date": "2025-12-01",
        "birth_date": "1990-05-15",
        "form_code": "FORM_19",
        "aadhaar_kyc": True,
        "bank_kyc": True,
        "employer_dsc_approved": True,
        "establishment_closed": False,
        "wage_paise": 1500000,
        "claim_amount_paise": 50000000,  # ₹5 Lakhs
    }

    response = client.post("/v1/member/evaluate", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["evaluation_id"].startswith("EVAL-MEM-")
    assert data["eligible"] is True
    assert len(data["blockers"]) == 0
    assert len(data["working_steps"]) > 0
    assert len(data["rule_snapshot_hash"]) == 64


def test_member_evaluate_closed_establishment_fallback():
    """
    When establishment is closed, employer DSC requirement is waived
    and offline bank manager attestation pathway is provided.
    """
    payload = {
        "joining_date": "2020-01-01",
        "exit_date": "2025-12-01",
        "birth_date": "1990-05-15",
        "form_code": "FORM_19",
        "aadhaar_kyc": True,
        "bank_kyc": True,
        "employer_dsc_approved": False,
        "establishment_closed": True,  # Closed establishment
    }

    response = client.post("/v1/member/evaluate", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["eligible"] is True
    preflight = data["calculation_results"]["preflight"]
    assert preflight["offline_fallback_available"] is True
    assert any("Bank Manager" in s for s in data["working_steps"])


# ============================================================================
# 4. EMPLOYER EVALUATION ENDPOINT TESTS (POST /v1/employer/evaluate)
# ============================================================================

def test_employer_evaluate_wage_ceiling_and_penalties():
    """
    Evaluates employer coverage, 50% allowance add-back, and late ECR penalties
    (12% p.a. Section 7Q + Section 14B damages + 25% Section 7O pre-deposit).
    """
    payload = {
        "employee_count": 45,
        "branch_count": 1,
        "basic_wages_paise": 1000000,       # ₹10,000
        "gross_wages_paise": 2500000,       # ₹25,000
        "excluded_allowances_paise": 1500000,  # ₹15,000 (> 50% threshold of ₹12,500 -> ₹2,500 add-back)
        "wage_month": "2026-01-01",
        "due_date": "2026-02-15",
        "payment_date": "2026-04-21",       # 65 days late
        "remittance_amount_paise": 5000000, # ₹50,000 assessed
        "member_age": 35,
    }

    response = client.post("/v1/employer/evaluate", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["evaluation_id"].startswith("EVAL-EMP-")
    assert data["covered"] is True
    wages_res = data["calculation_results"]["wages_contributions"]
    assert wages_res["excess_allowances_added_back_paise"] == 250000
    assert wages_res["adjusted_statutory_wage_paise"] == 1250000

    # Penalties breakdown
    penalties = data["penalties"]
    assert penalties is not None
    assert penalties["days_delayed"] == 65
    assert penalties["interest_7q_paise"] > 0
    assert penalties["damages_14b_paise"] > 0
    assert penalties["appeal_deposit_7o_paise"] == 1314200  # Exactly 25% of ₹52,568.49 rounded to ₹13,142


# ============================================================================
# 5. PORTAL TROUBLESHOOTING & GAP LOOP TESTS (POST /v1/portal/troubleshoot)
# ============================================================================

def test_portal_troubleshoot_known_error():
    """
    Known portal error returns actionable workaround steps from Tier 4 KB.
    """
    payload = {
        "portal_side": "employer",
        "error_code": "ERR_DSC_NOT_REGISTERED",
    }
    response = client.post("/v1/portal/troubleshoot", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["found"] is True
    assert data["engine_gap_event_logged"] is False
    assert len(data["solutions"]) == 1
    assert "DSC" in data["solutions"][0]["description"]


def test_portal_troubleshoot_unknown_error_emits_gap_event():
    """
    Unrecognized error automatically emits an EngineGapEvent into Stage 3.
    """
    payload = {
        "portal_side": "member",
        "error_code": "ERR_UNKNOWN_NEW_VOD_TOKEN_404",
        "screenshot_text": "Session timed out during OTP handshake",
    }
    response = client.post("/v1/portal/troubleshoot", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["found"] is False
    assert data["engine_gap_event_logged"] is True


# ============================================================================
# 6. CITATION-LOCKED PRECEDENTS RAG TESTS (POST /v1/cases/precedents)
# ============================================================================

def test_precedents_search_citation_locked():
    """
    Querying precedents returns verified excerpts with matching SHA-256 hashes
    and citation-lock status VERIFIED_LOCKED.
    """
    payload = {
        "query_text": "damages Section 14B civil obligation mens rea",
        "section": "14B",
    }
    response = client.post("/v1/cases/precedents", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["total_results"] >= 1
    assert data["citation_lock_status"] == "VERIFIED_LOCKED"
    top_citation = data["citations"][0]
    assert len(top_citation["doc_sha256"]) == 64
    assert top_citation["citation_lock_verified"] is True
    assert "civil obligation" in top_citation["verbatim_excerpt"].lower()


# ============================================================================
# 7. POINT-IN-TIME STATUTORY RULES LOOKUP (GET /v1/rules/as-of)
# ============================================================================

def test_point_in_time_rules_lookup_boundary_shifts():
    """
    Point-in-time statutory lookup resolves historical, active, and boundary dates.
    """
    # 1. Pre-2014 ceiling (₹6,500 = 650,000 paise)
    res_pre = client.get(
        "/v1/rules/as-of?rule_key=statutory_wage_ceiling&event_date=2014-08-31",
        headers=AUTH_HEADERS,
    )
    assert res_pre.status_code == 200
    assert res_pre.json()["value_numeric"] == 650000

    # 2. 2014-2026 ceiling (₹15,000 = 1,500,000 paise)
    res_mid = client.get(
        "/v1/rules/as-of?rule_key=statutory_wage_ceiling&event_date=2024-05-01",
        headers=AUTH_HEADERS,
    )
    assert res_mid.status_code == 200
    assert res_mid.json()["value_numeric"] == 1500000

    # 3. Post-Sept 17, 2026 ceiling (₹25,000 = 2,500,000 paise)
    res_post = client.get(
        "/v1/rules/as-of?rule_key=statutory_wage_ceiling&event_date=2026-09-17",
        headers=AUTH_HEADERS,
    )
    assert res_post.status_code == 200
    assert res_post.json()["value_numeric"] == 2500000


# ============================================================================
# 8. FEEDBACK & DISCREPANCY FLAGGING (POST /v1/feedback/flag)
# ============================================================================

def test_feedback_flag_endpoint():
    """
    User/officer feedback is accepted, generates a ticket ID, and queues a crawl.
    """
    payload = {
        "rule_key": "statutory_wage_ceiling",
        "notes": "Notification gazetted with new exemption list for north-east states.",
    }
    response = client.post("/v1/feedback/flag", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["ticket_id"].startswith("TCK-")
    assert data["status"] == "QUEUED"
    assert data["verification_crawl_queued"] is True


# ============================================================================
# 9. BATCH ECR FILE VALIDATION TESTS (POST /v1/employer/ecr/validate-file)
# ============================================================================

def test_ecr_file_validation_success():
    """
    Validates a well-formed ECR file with compliant 12% EE math and wage caps.
    """
    # UAN#~#Name#~#Gross#~#EPF#~#EPS#~#EDLI#~#EE_EPF#~#EPS_Contr#~#ER_EPF_Diff#~#NCP#~#Refund
    ecr_sample = (
        "100123456789#~#Amit Kumar#~#20000.00#~#15000.00#~#15000.00#~#15000.00#~#1800.00#~#1250.00#~#550.00#~#0#~#0.00\n"
        "100987654321#~#Pooja Sharma#~#12000.00#~#12000.00#~#12000.00#~#12000.00#~#1440.00#~#1000.00#~#440.00#~#2#~#0.00\n"
    )
    payload = {
        "wage_month": "2026-03-01",
        "file_content": ecr_sample,
    }
    response = client.post("/v1/employer/ecr/validate-file", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 2
    assert data["valid_records"] == 2
    assert data["invalid_records"] == 0
    assert data["is_valid_for_upload"] is True
    assert data["total_ee_contribution_paise"] == (180000 + 144000)
    assert data["total_admin_charges_paise"] >= 50000


def test_ecr_file_validation_catches_math_and_ceiling_errors():
    """
    Detects math errors, excessive EPS wage capping, and out-of-bounds NCP days.
    """
    corrupt_ecr = (
        # Row 1: EE EPF is ₹1,000 instead of 12% on ₹15,000 (₹1,800) -> EE_CONTRIBUTION_MATH_MISMATCH
        "100111111111#~#Bad Math#~#15000.00#~#15000.00#~#15000.00#~#15000.00#~#1000.00#~#1250.00#~#550.00#~#0#~#0.00\n"
        # Row 2: EPS wages ₹20,000 exceeds ₹15,000 statutory ceiling in early 2026
        "100222222222#~#Ceiling Breach#~#25000.00#~#25000.00#~#20000.00#~#15000.00#~#3000.00#~#1250.00#~#1750.00#~#0#~#0.00\n"
        # Row 3: NCP days is 45 (> 31) -> NCP_DAYS_OUT_OF_BOUNDS
        "100333333333#~#Bad NCP#~#10000.00#~#10000.00#~#10000.00#~#10000.00#~#1200.00#~#833.00#~#367.00#~#45#~#0.00\n"
    )
    payload = {
        "wage_month": "2026-03-01",
        "file_content": corrupt_ecr,
    }
    response = client.post("/v1/employer/ecr/validate-file", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["is_valid_for_upload"] is False
    assert len(data["errors"]) >= 3
    error_codes = [e["error_code"] for e in data["errors"]]
    assert "EE_CONTRIBUTION_MATH_MISMATCH" in error_codes
    assert "EPS_WAGE_EXCEEDS_STATUTORY_CEILING" in error_codes
    assert "NCP_DAYS_OUT_OF_BOUNDS" in error_codes


# ============================================================================
# 10. CITATION-LOCKED LEGAL DRAFT TESTS
# ============================================================================

def test_draft_epfigms_grievance_endpoint():
    """
    Verifies that the EPFiGMS drafting endpoint generates a formal petition
    with speaking order circular citation and SLA references.
    """
    payload = {
        "member_name": "Rajesh Kumar",
        "uan": "100234567890",
        "claim_id": "CLM-2026-9921",
        "form_code": "FORM_19",
        "rejection_reason": "Employer signature mismatch on bank cheque",
        "submission_date": "2026-02-01",
    }
    response = client.post("/v1/legal/draft/epfigms", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["document_type"] == "EPFIGMS_GRIEVANCE"
    assert "Speaking Order" in data["body_markdown"]
    assert "WSU/10(1)2011/Changes in Software/34138" in data["body_markdown"]
    assert any("20 Days" in str(c) for c in data["statutory_citations"])


def test_draft_cgit_appeal_endpoint():
    """
    Verifies that the CGIT Appeal Memo endpoint calculates and incorporates
    the statutory 25% Section 7O pre-deposit.
    """
    payload = {
        "establishment_name": "ABC Infotech Private Limited",
        "establishment_code": "DLCPM0012345000",
        "impugned_order_ref": "7A/DL/2026/8812",
        "impugned_order_date": "2026-01-15",
        "assessed_arrears_paise": 20000000,   # ₹2,00,000
        "interest_7q_paise": 2400000,         # ₹24,000
        "damages_14b_paise": 5000000,         # ₹50,000
        "pre_deposit_25_paise": 6850000,      # ₹68,500 (25% of ₹2,74,000)
        "bench_city": "New Delhi",
    }
    response = client.post("/v1/legal/draft/cgit-appeal", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["document_type"] == "CGIT_APPEAL_7I"
    assert "SECTION 7-I" in data["body_markdown"]
    assert "25.00%" in data["body_markdown"]
    assert "₹68,500.00" in data["body_markdown"]
    assert len(data["case_precedents"]) > 0


# ============================================================================
# 11. RESILIENT LIVE PROBE CLIENT TESTS
# ============================================================================

def test_live_probe_client_boundaries_and_304_caching():
    """
    Verifies that LiveProbeClient blocks non-.gov.in domains and issues
    lightweight conditional 304 probes on repeat visits.
    """
    from ingest.workers.live_probe_client import ResilientLiveProbeClient

    client_probe = ResilientLiveProbeClient()

    # 1. Non-gov boundary blocked
    res_blocked = client_probe.probe_url("https://malicious-phishing-epfo.com/fake.pdf")
    assert res_blocked.status_code == 403
    assert "Security Violation" in res_blocked.error_message

    # 2. First probe on official domain -> 200 with new content
    url = "https://epfindia.gov.in/circulars/dummy_notice.pdf"
    content = b"%PDF-1.4 official circular content"
    res_1 = client_probe.probe_url(url, mock_content=content)
    assert res_1.status_code == 200
    assert res_1.is_modified is True
    assert len(res_1.content_sha256) == 64

    # 3. Second probe without changes -> 304 Not Modified
    res_2 = client_probe.probe_url(url, mock_content=content)
    assert res_2.status_code == 304
    assert res_2.is_modified is False
    assert res_2.content_bytes == b""
