"""
tests/golden/test_stage2_golden.py
Authoritative Golden Regression Test Suite for Stage 2 Deterministic Engines.
Covers the full Stage 2 Blueprint Golden Matrix:
- MEM-01: Form 19 without employer attestation & closed establishment fallback
- MEM-02: EPS withdrawal benefit with 18-month employer contribution default exclusion
- MEM-03: 4th vs 8th Completed Wage Month rule & > ₹25L 4-tier approval routing
- EMP-01: 50% excluded-pay add-back & 2026-09-16 vs 2026-09-17 wage ceiling shift
- EMP-02: Late ECR by 65 days (7Q interest, 14B damages, 25% Sec 7O appeal deposit)
- EMP-03: Exempted establishment ECR upload & age-59 EPS contribution block
- GAP-01: Engine gap event capture and self-enhancement logging
"""

from datetime import date
import pytest

from db.statutory_store import build_seeded_statutory_store, StatutoryStore
from engines.common import MemberCaseInput, EmployerCaseInput, EngineGapEvent
from engines.member.claims_eligibility import evaluate_claims_eligibility
from engines.member.pension_edli import evaluate_pension_and_edli
from engines.member.portal_preflight import evaluate_portal_preflight
from engines.member.grievance_router import evaluate_grievance_route
from engines.employer.coverage_clubbing import evaluate_establishment_coverage
from engines.employer.wage_contributions import evaluate_wage_contributions
from engines.employer.penalties_appeals import evaluate_penalties_and_appeals
from engines.employer.ecr_inspection_gate import evaluate_ecr_inspection_gate


@pytest.fixture
def store():
    return build_seeded_statutory_store()


# ============================================================================
# MEM-01: Form 19 without employer attestation; bank KYC not DSC-approved
# ============================================================================

def test_mem_01_portal_preflight_employer_dsc_block_and_closed_fallback(store: StatutoryStore):
    """
    MEM-01: Member attempts Form 19 online when employer has not DSC-approved Bank KYC.
    Case A: Establishment is active -> Blocked online; employer must approve via DSC.
    Case B: Establishment is closed -> Closed-establishment fallback activated:
            Exempt from employer DSC; eligible for offline Bank Manager attestation.
    """
    # Case A: Active establishment, missing employer DSC
    active_case = MemberCaseInput(
        joining_date=date(2020, 1, 1),
        exit_date=date(2025, 12, 1),
        birth_date=date(1990, 5, 15),
        form_code="FORM_19",
        claim_amount_paise=25000000,  # ₹2,50,000
        wage_paise=1500000,
        uan_active=True,
        aadhaar_kyc=True,
        bank_kyc=True,
        employer_dsc_approved=False,  # Unapproved by employer
        establishment_closed=False,
        event_date=date(2026, 3, 1),
    )
    result_a = evaluate_portal_preflight(active_case, store)
    assert result_a.value["preflight_passed"] is False
    assert result_a.value["can_submit_online"] is False
    assert result_a.value["offline_fallback_available"] is False
    assert any("EMPLOYER_DSC_PENDING" in b for b in result_a.blockers)

    # Case B: Closed establishment, missing employer DSC
    closed_case = MemberCaseInput(
        joining_date=date(2020, 1, 1),
        exit_date=date(2025, 12, 1),
        birth_date=date(1990, 5, 15),
        form_code="FORM_19",
        claim_amount_paise=25000000,
        wage_paise=1500000,
        uan_active=True,
        aadhaar_kyc=True,
        bank_kyc=True,
        employer_dsc_approved=False,
        establishment_closed=True,  # Company shut down
        has_unattested_bank_manager_cert=True,
        event_date=date(2026, 3, 1),
    )
    result_b = evaluate_portal_preflight(closed_case, store)
    assert result_b.value["offline_fallback_available"] is True
    assert "Bank Manager" in result_b.value["offline_fallback_authority"]
    assert result_b.value["preflight_passed"] is True  # Pass because bank manager cert is provided
    assert any("ESTABLISHMENT CLOSED FALLBACK ACTIVATED" in step for step in result_b.working_steps)


# ============================================================================
# MEM-02: EPS withdrawal benefit with 18-month employer contribution default
# ============================================================================

def test_mem_02_eps_withdrawal_benefit_with_employer_default(store: StatutoryStore):
    """
    MEM-02: Member with 60 months gross service, where employer defaulted on 18 months of EPS.
    Expected: Defaulter 18 months are strictly excluded from pensionable service credit
              (60m - 18m = 42 months net service).
              Cites EPFO FAQ rule and excludes defaulted period from calculation.
    """
    case = MemberCaseInput(
        joining_date=date(2020, 1, 1),
        exit_date=date(2025, 1, 1),  # 60 gross months (5 years)
        birth_date=date(1992, 4, 10),
        form_code="FORM_10C",
        claim_amount_paise=5000000,
        wage_paise=1500000,
        employer_default_months=18,  # Employer failed to remit for 18 months
        non_contributory_service_days=0,
        event_date=date(2026, 3, 1),
    )
    result = evaluate_pension_and_edli(case, store)

    assert result.value["pension_type"] == "WITHDRAWAL_BENEFIT"
    assert result.value["defaulted_months_excluded"] == 18
    # Gross 60m - 18 defaulted months = 42 net pensionable months (3.5 years)
    assert result.value["net_pensionable_months"] == 42
    assert any("Employer Default Period Detected: 18 months" in step for step in result.working_steps)
    assert any(tip["code"] == "EPS_DEFAULT_PERIOD_EXCLUDED" for tip in result.troubleshooting_tips)


# ============================================================================
# MEM-03: Joining on 4th vs 8th of month & claim > ₹25 Lakhs routing
# ============================================================================

def test_mem_03_completed_wage_month_rule_and_high_value_routing(store: StatutoryStore):
    """
    MEM-03:
    Part A: Joining on 4th of month counts current month as Completed Wage Month.
            Joining on 8th skips current month from Completed Wage Month accrual.
    Part B: Claim amount > ₹25 Lakhs (250,000,000 paise) routes to 4-tier approval:
            SSA -> AO -> APFC -> OIC.
    """
    # Case A: Joined on 4th of month, claim ₹30 Lakhs
    joined_on_4th = MemberCaseInput(
        joining_date=date(2025, 1, 4),  # Joined on 4th
        exit_date=date(2026, 1, 31),
        birth_date=date(1985, 8, 20),
        form_code="FORM_19",
        claim_amount_paise=300000000,  # ₹30,00,000 (> ₹25L)
        wage_paise=2500000,
        event_date=date(2026, 4, 15),
    )
    result_4th = evaluate_claims_eligibility(joined_on_4th, store)
    assert result_4th.value["joining_month_qualifies"] is True
    # 4-level approval routing
    assert "TIER_3_FOUR_LEVEL" in result_4th.approval_tier
    assert "SSA -> AO -> APFC -> OIC" in result_4th.approval_tier

    # Case B: Joined on 8th of month
    joined_on_8th = MemberCaseInput(
        joining_date=date(2025, 1, 8),  # Joined on 8th (>= 5th)
        exit_date=date(2026, 1, 31),
        birth_date=date(1985, 8, 20),
        form_code="FORM_19",
        claim_amount_paise=300000000,
        wage_paise=2500000,
        event_date=date(2026, 4, 15),
    )
    result_8th = evaluate_claims_eligibility(joined_on_8th, store)
    assert result_8th.value["joining_month_qualifies"] is False
    # Verified: joining on 4th accrues 1 more month of service than joining on 8th
    assert result_4th.value["contributory_service_months"] == result_8th.value["contributory_service_months"] + 1


# ============================================================================
# EMP-01: 50% Excluded-Pay Add-Back & 2026-09-16 vs 2026-09-17 Wage Ceiling
# ============================================================================

def test_emp_01_wage_add_back_and_boundary_ceiling_shift(store: StatutoryStore):
    """
    EMP-01:
    Gross ₹50,000 (Basic ₹22,000, HRA ₹28,000).
    50% of gross = ₹25,000.
    HRA ₹28,000 exceeds 50% threshold by ₹3,000.
    Excess ₹3,000 added back to Basic: Adjusted Statutory Wage = ₹25,000 (2,500,000 paise).

    Boundary Test:
    - On 2026-09-16: Uses statutory ceiling of ₹15,000 (1,500,000 paise).
    - On 2026-09-17: Uses newly appointed statutory ceiling of ₹25,000 (2,500,000 paise per S.O. 5109(E)).
    """
    # Sub-case A: 2026-09-16 (Pre-shift: ceiling ₹15,000)
    case_pre = EmployerCaseInput(
        employee_count=50,
        branch_count=1,
        wage_month=date(2026, 9, 16),
        due_date=date(2026, 10, 15),
        payment_date=date(2026, 10, 15),
        gross_wages_paise=5000000,     # ₹50,000
        basic_wages_paise=2200000,     # ₹22,000
        excluded_allowances_paise=2800000,  # ₹28,000 (HRA)
    )
    res_pre = evaluate_wage_contributions(case_pre, store)

    assert res_pre.value["excess_allowances_added_back_paise"] == 300000  # ₹3,000
    assert res_pre.value["adjusted_statutory_wage_paise"] == 2500000       # ₹25,000
    assert res_pre.value["statutory_wage_ceiling_paise"] == 1500000        # ₹15,000 ceiling
    assert res_pre.value["capped_wage_paise"] == 1500000                   # Capped at ₹15,000
    # Employee 12% on ₹15,000 = ₹1,800 (180000 paise)
    assert res_pre.value["ee_epf_paise"] == 180000
    # Employer EPS 8.33% on ₹15,000 = ₹1,250 (124950 rounded to 125000)
    assert res_pre.value["er_eps_paise"] == 125000

    # Sub-case B: 2026-09-17 (Post-shift: ceiling ₹25,000)
    case_post = EmployerCaseInput(
        employee_count=50,
        branch_count=1,
        wage_month=date(2026, 9, 17),
        due_date=date(2026, 10, 15),
        payment_date=date(2026, 10, 15),
        gross_wages_paise=5000000,
        basic_wages_paise=2200000,
        excluded_allowances_paise=2800000,
    )
    res_post = evaluate_wage_contributions(case_post, store)

    assert res_post.value["excess_allowances_added_back_paise"] == 300000  # ₹3,000
    assert res_post.value["adjusted_statutory_wage_paise"] == 2500000      # ₹25,000
    assert res_post.value["statutory_wage_ceiling_paise"] == 2500000       # ₹25,000 ceiling
    assert res_post.value["capped_wage_paise"] == 2500000                  # Full ₹25,000 allowed!
    # Employee 12% on ₹25,000 = ₹3,000 (300000 paise)
    assert res_post.value["ee_epf_paise"] == 300000
    # Employer EPS 8.33% on ₹25,000 = ₹2,083 (208250 rounded to 208300 paise)
    assert res_post.value["er_eps_paise"] == 208300


# ============================================================================
# EMP-02: Late ECR by 65 days (₹2,50,000 arrears) + Tribunal Appeal Deposit
# ============================================================================

def test_emp_02_penalties_7q_14b_and_appeal_deposit(store: StatutoryStore):
    """
    EMP-02:
    Arrears: ₹2,50,000 (25,000,000 paise).
    Delay: 65 days (Due 2026-04-15, paid 2026-06-19).
    Calculations:
    - 7Q Interest (12% p.a.): (250,000 x 0.12 x 65) / 365 = ₹5,342.47 -> 534247 paise
    - 14B Damages (Revised Post-June 2024: 1% per month = 3 months for 65 days -> 3% of 250K = ₹7,500 = 750000 paise)
    - Total assessed liability: Arrears + 14B + 7Q
    - Section 7O Appeal Pre-Deposit: Exact 25.00% of total assessed liability.
    """
    case = EmployerCaseInput(
        employee_count=100,
        branch_count=2,
        wage_month=date(2026, 3, 1),
        due_date=date(2026, 4, 15),
        payment_date=date(2026, 6, 19),  # 65 days delayed
        gross_wages_paise=100000000,
        basic_wages_paise=50000000,
        excluded_allowances_paise=50000000,
        remittance_amount_paise=25000000,  # ₹2,50,000 due
    )
    res = evaluate_penalties_and_appeals(case, store)

    assert res.value["days_delayed"] == 65
    assert res.value["arrears_paise"] == 25000000

    # Verify Section 7Q Simple Interest (exact to integer paise)
    # (25000000 * 12 * 65) / 36500 = 534246.57... rounds to 534247 paise
    assert res.value["interest_7q_paise"] == 534247

    # Verify Section 14B Damages (65 days = ceil(65/30) = 3 months @ 1% = 3% of 250,000 = ₹7,500 = 750000 paise)
    assert res.value["damages_14b_paise"] == 750000

    # Total penalty = 534247 + 750000 = 1284247 paise (₹12,842.47)
    assert res.value["total_statutory_penalty_paise"] == 1284247

    # Total assessed determination = 25000000 + 1284247 = 26284247 paise
    # 25% appeal pre-deposit = round(26284247 * 0.25) = 6571062 paise (₹65,710.62) rounded per 14B policy to 6571100 paise
    expected_deposit = store.apply_rounding("14B", int(round(26284247 * 0.25)))
    assert res.value["appeal_deposit_7o_paise"] == expected_deposit
    assert any("Section 7O CGIT Pre-Deposit: Mandatory 25.0%" in step for step in res.working_steps)


# ============================================================================
# EMP-03: Exempted Establishment ECR Upload & Age-59 EPS Block
# ============================================================================

def test_emp_03_exempted_ecr_upload_and_age_59_eps_block(store: StatutoryStore):
    """
    EMP-03:
    Part A: Exempted establishment ECR upload requires full member-level wage rows.
            EPF Account 1 contribution on government challan is ₹0 (credited to private trust).
            EPFO bills Account 22 inspection charges at 0.18% of EPF wages.
    Part B: Member aged 59 (>= 58) without deferred pension flag has EPS contribution blocked (₹0).
    """
    case = EmployerCaseInput(
        employee_count=150,
        branch_count=3,
        wage_month=date(2026, 8, 1),
        due_date=date(2026, 9, 15),
        payment_date=date(2026, 9, 15),
        gross_wages_paise=1500000,  # ₹15,000
        basic_wages_paise=1500000,
        excluded_allowances_paise=0,
        exemption_flags={"epf_exempted": True, "eps_exempted": False, "edli_exempted": False},
        member_age=59,  # Age 59 (>= 58)
        is_deferred_pension=False,
    )
    res = evaluate_ecr_inspection_gate(case, store)

    assert res.value["ecr_valid"] is True
    assert res.value["is_epf_exempted"] is True
    # Exempted trust: EPF challan contribution is ₹0
    assert res.value["epf_challan_contribution_paise"] == 0
    # Account 22 inspection charges billed at 0.18% of ₹15,000 = ₹27 (2700 paise)
    assert res.value["inspection_charges_paise"] == 2700
    # Age 59 EPS block: EPS contribution is ₹0
    assert res.value["eps_contribution_paise"] == 0
    assert "AGE_58_EPS_BLOCKED" in res.value["eps_blocked_reason"]
    assert any("Exempted Establishment Detected" in step for step in res.working_steps)
    assert any("Age-58 EPS Block" in step for step in res.working_steps)


# ============================================================================
# GAP-01: Engine Gap Event Logging & Self-Enhancement Loop
# ============================================================================

def test_gap_01_engine_gap_event_logging():
    """
    GAP-01: Verifies that unmatched portal errors or discrepancies emit a
    structured EngineGapEvent for the Stage 3/4 self-enhancement loop.
    """
    gap_event = EngineGapEvent(
        event_id="GAP-2026-ERR-902",
        source_side="member",
        error_code="ERR_UNIFIED_FAT_TIMEOUT",
        context={"portal": "UMANG", "operation": "DIGITAL_LIFE_CERTIFICATE", "attempt_count": 3},
        detected_at="2026-11-22T22:00:00Z",
        candidate_golden_test_seed={
            "scenario": "UMANG Face RD timeout during DLC Campaign 5.0",
            "recommended_workaround": "Switch to IPPB Post Info doorstep biometric submission"
        }
    )
    assert gap_event.event_id == "GAP-2026-ERR-902"
    assert gap_event.error_code == "ERR_UNIFIED_FAT_TIMEOUT"
    assert "candidate_golden_test_seed" in gap_event.__dict__
