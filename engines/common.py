"""
engines/common.py
Core typed contracts, case input structures, and citation envelope models
for the Stage 2 Member and Employer deterministic rule engines.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class EngineResult:
    """
    Standardized, 100% auditable citation envelope returned by all Stage 2 engines.
    """
    value: Any
    working_steps: List[str]
    blockers: List[str]
    approval_tier: Optional[str]
    judicial_notes: Optional[str]
    troubleshooting_tips: List[Dict[str, Any]]
    rule_id: str
    citation_url: str
    doc_sha256: str
    evaluated_as_of_date: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "working_steps": self.working_steps,
            "blockers": self.blockers,
            "approval_tier": self.approval_tier,
            "judicial_notes": self.judicial_notes,
            "troubleshooting_tips": self.troubleshooting_tips,
            "rule_id": self.rule_id,
            "citation_url": self.citation_url,
            "doc_sha256": self.doc_sha256,
            "evaluated_as_of_date": self.evaluated_as_of_date,
            "metadata": self.metadata,
        }


@dataclass
class MemberCaseInput:
    """
    Typed input contract for Member-side claims, pension, and portal preflight evaluations.
    All monetary amounts are strictly in integer paise (₹1 = 100 paise).
    """
    joining_date: date
    birth_date: date
    form_code: str  # "FORM_19", "FORM_10C", "FORM_31", "JOINT_DECLARATION"
    claim_amount_paise: int
    wage_paise: int
    uan_active: bool = True
    aadhaar_kyc: bool = True
    bank_kyc: bool = True
    employer_dsc_approved: bool = True
    exit_date: Optional[date] = None
    establishment_closed: bool = False
    has_unattested_bank_manager_cert: bool = False
    employer_default_months: int = 0
    non_contributory_service_days: int = 0
    advance_purpose: Optional[str] = None  # "illness", "marriage", "education", "housing", "special"
    event_date: Optional[date] = None

    @property
    def evaluation_date(self) -> date:
        return self.event_date or date.today()

    @property
    def age(self) -> int:
        d = self.evaluation_date
        return d.year - self.birth_date.year - ((d.month, d.day) < (self.birth_date.month, self.birth_date.day))


@dataclass
class EmployerCaseInput:
    """
    Typed input contract for Employer-side coverage, contributions, 7Q/14B penalties, and ECR gate.
    All monetary amounts are strictly in integer paise (₹1 = 100 paise).
    """
    employee_count: int
    branch_count: int
    wage_month: date
    due_date: date
    payment_date: date
    gross_wages_paise: int
    basic_wages_paise: int
    excluded_allowances_paise: int
    exemption_flags: Dict[str, bool] = field(default_factory=lambda: {
        "epf_exempted": False,
        "eps_exempted": False,
        "edli_exempted": False,
    })
    member_age: int = 30
    member_joining_date: Optional[date] = None
    is_deferred_pension: bool = False
    opted_higher_pension: bool = False
    remittance_amount_paise: int = 0
    jurisdiction_zone: str = "ALL"
    event_date: Optional[date] = None

    @property
    def evaluation_date(self) -> date:
        return self.event_date or date.today()


@dataclass
class EngineGapEvent:
    """
    Self-enhancement log emitted when an unmapped portal error code,
    discrepancy, or missing statutory permutation occurs.
    """
    event_id: str
    source_side: str  # "member", "employer"
    error_code: str
    context: Dict[str, Any]
    detected_at: str
    candidate_golden_test_seed: Dict[str, Any]
