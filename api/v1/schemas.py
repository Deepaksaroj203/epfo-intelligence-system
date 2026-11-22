"""
api/v1/schemas.py
Pydantic Request & Response schemas for Stage 5 Production FastAPI Endpoints.
All monetary amounts are strictly in integer paise. Zero hardcoded law.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# 1. MEMBER EVALUATION SCHEMAS
# ============================================================================

class MemberEvaluateRequest(BaseModel):
    joining_date: date
    birth_date: date
    form_code: str
    claim_amount_paise: int = 0
    wage_paise: int = 1500000
    uan_active: bool = True
    aadhaar_kyc: bool = True
    bank_kyc: bool = True
    employer_dsc_approved: bool = True
    exit_date: Optional[date] = None
    establishment_closed: bool = False
    has_unattested_bank_manager_cert: bool = False
    employer_default_months: int = 0
    non_contributory_service_days: int = 0
    advance_purpose: Optional[str] = None
    event_date: Optional[date] = None


class MemberEvaluateResponse(BaseModel):
    evaluation_id: str
    eligible: bool
    status: str
    approval_tier: Optional[str]
    blockers: List[str]
    working_steps: List[str]
    calculation_results: Dict[str, Any]
    troubleshooting_tips: List[Dict[str, Any]] = Field(default_factory=list)
    rule_snapshot_hash: str
    citation_url: str
    doc_sha256: str
    degraded_mode: bool = False


# ============================================================================
# 2. EMPLOYER EVALUATION SCHEMAS
# ============================================================================

class EmployerEvaluateRequest(BaseModel):
    employee_count: int
    branch_count: int = 1
    wage_month: date
    due_date: date
    payment_date: date
    gross_wages_paise: int
    basic_wages_paise: int
    excluded_allowances_paise: int = 0
    exemption_flags: Dict[str, bool] = Field(default_factory=dict)
    member_age: int = 30
    member_joining_date: Optional[date] = None
    is_deferred_pension: bool = False
    opted_higher_pension: bool = False
    remittance_amount_paise: int = 0
    jurisdiction_zone: str = "ALL"
    event_date: Optional[date] = None


class EmployerEvaluateResponse(BaseModel):
    evaluation_id: str
    covered: bool
    working_steps: List[str]
    blockers: List[str]
    calculation_results: Dict[str, Any]
    penalties: Optional[Dict[str, Any]] = None
    rule_snapshot_hash: str
    citation_url: str
    doc_sha256: str
    degraded_mode: bool = False


# ============================================================================
# 3. PORTAL TROUBLESHOOTING SCHEMAS
# ============================================================================

class PortalTroubleshootRequest(BaseModel):
    portal_side: str  # "member" | "employer" | "unified"
    error_code: str
    form_code: Optional[str] = None
    screenshot_text: Optional[str] = None


class PortalWorkaroundSchema(BaseModel):
    error_code: str
    description: str
    workaround_steps: List[str]
    root_cause: str
    confidence_score: float
    confirmed_by_official: bool


class PortalTroubleshootResponse(BaseModel):
    found: bool
    solutions: List[PortalWorkaroundSchema]
    engine_gap_event_logged: bool
    disclaimer: str


# ============================================================================
# 4. PRECEDENTS & CITATION-LOCKED RAG SCHEMAS
# ============================================================================

class PrecedentsSearchRequest(BaseModel):
    query_text: str
    section: Optional[str] = None  # "7A" | "14B" | "7Q" | "7O"
    jurisdiction_zone: Optional[str] = None


class PrecedentCitationSchema(BaseModel):
    case_number: str
    case_title: str
    court_or_tribunal: str
    order_date: str
    doc_sha256: str
    citation_url: str
    key_holding: str
    verbatim_excerpt: str
    citation_lock_verified: bool


class PrecedentsSearchResponse(BaseModel):
    total_results: int
    citations: List[PrecedentCitationSchema]
    citation_lock_status: str  # "VERIFIED_LOCKED" | "PARTIAL"


# ============================================================================
# 5. POINT-IN-TIME RULES SCHEMAS
# ============================================================================

class RuleAsOfResponse(BaseModel):
    rule_key: str
    scope: Dict[str, Any]
    event_date: str
    value_numeric: Optional[int]
    value_type: str
    effective_from: str
    effective_to: Optional[str]
    precedence_rank: int
    citation_url: str
    doc_sha256: str
    verbatim_quote: str
    is_stayed: bool = False
    stay_details: Optional[Dict[str, Any]] = None


# ============================================================================
# 6. FEEDBACK & GAP CAPTURE SCHEMAS
# ============================================================================

class FeedbackFlagRequest(BaseModel):
    rule_id: Optional[str] = None
    rule_key: Optional[str] = None
    circular_ref: Optional[str] = None
    notes: str
    error_screenshot_base64: Optional[str] = None


class FeedbackFlagResponse(BaseModel):
    ticket_id: str
    status: str
    message: str
    verification_crawl_queued: bool


# ============================================================================
# 7. BATCH ECR FILE VALIDATION SCHEMAS
# ============================================================================

class ECRValidateFileRequest(BaseModel):
    wage_month: date
    file_content: str


class ECRRowErrorSchema(BaseModel):
    row_number: int
    uan: str
    member_name: str
    field_name: str
    error_code: str
    error_message: str
    statutory_citation: str


class ECRValidateFileResponse(BaseModel):
    total_records: int
    valid_records: int
    invalid_records: int
    total_epf_wages_paise: int
    total_ee_contribution_paise: int
    total_er_eps_paise: int
    total_er_epf_diff_paise: int
    total_admin_charges_paise: int
    errors: List[ECRRowErrorSchema]
    is_valid_for_upload: bool


# ============================================================================
# 8. CITATION-LOCKED LEGAL DOCUMENT DRAFTS
# ============================================================================

class EPFiGMSDraftRequest(BaseModel):
    member_name: str
    uan: str
    claim_id: str
    form_code: str
    rejection_reason: str
    submission_date: date
    regional_office: str = "Regional PF Commissioner"


class CGITAppealDraftRequest(BaseModel):
    establishment_name: str
    establishment_code: str
    impugned_order_ref: str
    impugned_order_date: date
    assessed_arrears_paise: int
    interest_7q_paise: int
    damages_14b_paise: int
    pre_deposit_25_paise: int
    bench_city: str = "New Delhi"


class LegalDraftResponse(BaseModel):
    document_type: str
    title: str
    recipient: str
    subject_line: str
    body_markdown: str
    statutory_citations: List[Dict[str, Any]]
    case_precedents: List[Dict[str, Any]]
