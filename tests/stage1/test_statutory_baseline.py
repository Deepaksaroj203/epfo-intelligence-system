"""
test_statutory_baseline.py
Stage 1 Automated Boundary-Date, Temporal Integrity & Citation Verification Test Suite.
Verifies all non-negotiable architectural requirements:
- Zero Hardcoded Law & Zero LLM Math (Integer paise resolution)
- Bitemporal & Non-Overlapping daterange constraints
- Strict Source Precedence & Judicial Override Interception
- Hash-Chain Tamper-Evident Verification on rule_change_log
- Exact Rounding Policies execution
- Citation Envelope Completeness
"""

from datetime import date
import pytest
from db.statutory_store import (
    build_seeded_statutory_store,
    StatutoryRuleRecord,
    JudicialOverrideRecord,
    StatutoryStore,
)


@pytest.fixture
def store():
    return build_seeded_statutory_store()


# ============================================================================
# 1. BOUNDARY-DATE WAGE CEILING RESOLUTION TESTS
# ============================================================================

def test_boundary_wage_ceiling_pre_2014(store: StatutoryStore):
    """
    On 2014-08-31 (the day before the 2014 revision),
    statutory wage ceiling must resolve to exactly ₹6,500 (650,000 paise).
    """
    envelope = store.get_rule_as_of("statutory_wage_ceiling", event_date=date(2014, 8, 31))
    assert envelope.value_numeric == 650000
    assert envelope.value_type == "integer_paise"
    assert envelope.precedence_rank == 10
    assert envelope.effective_from == "2001-06-01"
    assert envelope.effective_to == "2014-09-01"
    assert "Six thousand and five hundred rupees" in envelope.verbatim_quote
    assert len(envelope.doc_sha256) == 64


def test_boundary_wage_ceiling_post_2014_start(store: StatutoryStore):
    """
    On 2014-09-01 (effective date of G.S.R. 609(E)),
    statutory wage ceiling must jump immediately to ₹15,000 (1,500,000 paise).
    """
    envelope = store.get_rule_as_of("statutory_wage_ceiling", event_date=date(2014, 9, 1))
    assert envelope.value_numeric == 1500000
    assert envelope.value_type == "integer_paise"
    assert envelope.precedence_rank == 10
    assert envelope.effective_from == "2014-09-01"
    assert envelope.effective_to == "2026-09-17"
    assert "fifteen thousand rupees" in envelope.verbatim_quote
    assert envelope.doc_sha256 == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


def test_boundary_wage_ceiling_2026_pre_shift(store: StatutoryStore):
    """
    On 2026-09-16 (the day before the Sept 17, 2026 wage ceiling shift),
    the ceiling must still be exactly ₹15,000 (1,500,000 paise).
    """
    envelope = store.get_rule_as_of("statutory_wage_ceiling", event_date=date(2026, 9, 16))
    assert envelope.value_numeric == 1500000
    assert envelope.effective_to == "2026-09-17"


def test_boundary_wage_ceiling_2026_post_shift(store: StatutoryStore):
    """
    On 2026-09-17 (appointed date of S.O. 5109(E) / 2026 PIB notification),
    the ceiling must resolve deterministically to ₹25,000 (2,500,000 paise).
    """
    envelope = store.get_rule_as_of("statutory_wage_ceiling", event_date=date(2026, 9, 17))
    assert envelope.value_numeric == 2500000
    assert envelope.value_type == "integer_paise"
    assert envelope.effective_from == "2026-09-17"
    assert envelope.effective_to == "infinity"
    assert "Rs. 25,000 with effect from 17th September 2026" in envelope.verbatim_quote
    assert envelope.doc_sha256 == "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"


def test_future_wage_ceiling_in_active_regime(store: StatutoryStore):
    """
    On any future date (e.g. 2027-04-01), the ₹25,000 ceiling remains active.
    """
    envelope = store.get_rule_as_of("statutory_wage_ceiling", event_date=date(2027, 4, 1))
    assert envelope.value_numeric == 2500000


# ============================================================================
# 2. STATUTORY RATES & PENALTIES TESTS
# ============================================================================

def test_statutory_contribution_rates(store: StatutoryStore):
    """
    Verifies employee EPF (12.00%), employer EPS (8.33%), employer net EPF (3.67%), and EDLI (0.50%).
    """
    ee = store.get_rule_as_of("epf_employee_rate", event_date=date(2026, 6, 1))
    assert ee.value_numeric == 1200
    assert ee.value_type == "basis_points"

    er_eps = store.get_rule_as_of("eps_employer_rate", event_date=date(2026, 6, 1))
    assert er_eps.value_numeric == 833
    assert er_eps.value_type == "basis_points"

    er_epf = store.get_rule_as_of("epf_employer_net_rate", event_date=date(2026, 6, 1))
    assert er_epf.value_numeric == 367
    assert er_epf.value_type == "basis_points"

    edli = store.get_rule_as_of("edli_employer_rate", event_date=date(2026, 6, 1))
    assert edli.value_numeric == 50
    assert edli.value_type == "basis_points"


def test_delayed_payment_interest_7q(store: StatutoryStore):
    """
    Section 7Q simple interest must resolve to 12.00% p.a. (1200 bps).
    """
    res = store.get_rule_as_of("delayed_interest_7q_annual_rate", event_date=date(2026, 5, 29))
    assert res.value_numeric == 1200
    assert res.value_type == "basis_points"
    assert "simple interest at the rate of twelve per cent per annum" in res.verbatim_quote


def test_section_14b_damages_transition(store: StatutoryStore):
    """
    Verifies 14B damages transition from pre-June 2024 graded slabs to post-June 2024 revised uniform rate.
    """
    # Pre-revision: 2024-06-14 (legacy graded slabs)
    pre = store.get_rule_as_of("penal_damages_14b_slabs", event_date=date(2024, 6, 14))
    assert pre.value_type == "json_spec"
    assert pre.value_json is not None
    assert len(pre.value_json["slabs"]) == 4
    assert pre.value_json["slabs"][0]["rate_pa_percent"] == 5.0
    assert pre.value_json["slabs"][3]["rate_pa_percent"] == 25.0

    # Post-revision: 2024-06-15 (flat 12% p.a. / 1% per month)
    post = store.get_rule_as_of("penal_damages_14b_slabs", event_date=date(2024, 6, 15))
    assert post.value_numeric == 1200
    assert post.value_json["monthly_rate_bps"] == 100
    assert post.value_json["max_damages_cap_percent"] == 100


def test_section_7o_tribunal_appeal_deposit(store: StatutoryStore):
    """
    Mandatory 25% pre-deposit under Section 7O for CGIT appeals.
    """
    res = store.get_rule_as_of("tribunal_appeal_deposit_percent", event_date=date(2026, 6, 29))
    assert res.value_numeric == 2500  # 2500 bps = 25.00%
    assert res.value_type == "basis_points"


def test_excluded_allowances_50_percent_cap(store: StatutoryStore):
    """
    50% excluded allowance ceiling under Code on Social Security 2020 and SC 2019 precedent.
    """
    res = store.get_rule_as_of("excluded_allowances_cap_percent", event_date=date(2026, 1, 15))
    assert res.value_numeric == 5000  # 5000 bps = 50.00%
    assert res.precedence_rank == 5  # Judicial precedent rank


def test_coverage_headcount_threshold(store: StatutoryStore):
    """
    Coverage threshold: 20 employees.
    """
    res = store.get_rule_as_of("statutory_coverage_headcount", event_date=date(2026, 1, 1))
    assert res.value_numeric == 20


# ============================================================================
# 3. BITEMPORAL & EXCLUSION CONSTRAINT INTEGRITY (EXCLUDE USING gist)
# ============================================================================

def test_exclusion_constraint_rejects_overlapping_dates(store: StatutoryStore):
    """
    Enforces PostgreSQL EXCLUDE USING gist (rule_key WITH =, scope WITH =, effective_period WITH &&).
    Attempting to add an overlapping rule for the same rule_key and scope must raise an error.
    """
    # Existing rule covers 2014-09-01 to 2026-09-17
    # Attempting to insert an overlapping active rule covering 2025-01-01 to 2027-01-01
    conflicting_rule = StatutoryRuleRecord(
        rule_id="99999999-9999-9999-9999-999999999999",
        rule_key="statutory_wage_ceiling",
        scope={"side": "both", "establishment_type": "all", "worker_category": "domestic"},
        effective_from=date(2025, 1, 1),
        effective_to=date(2027, 1, 1),
        value_numeric=1800000,
        value_type="integer_paise",
        value_json=None,
        precedence_rank=10,
        status="active",
        citation_url="https://example.gov.in/conflict.pdf",
        doc_sha256="0000000000000000000000000000000000000000000000000000000000000000",
        verbatim_quote="Conflicting rule attempt",
        description="Conflicting rule",
    )

    with pytest.raises(ValueError) as excinfo:
        store.add_rule(conflicting_rule)

    assert "PostgreSQL Exclusion Constraint Violation" in str(excinfo.value)
    assert "statutory_wage_ceiling" in str(excinfo.value)


# ============================================================================
# 4. STRICT SOURCE PRECEDENCE & JUDICIAL OVERRIDE INTERCEPTION
# ============================================================================

def test_judicial_override_interception(store: StatutoryStore):
    """
    Verifies that an active Supreme Court / High Court order stays or overrides
    a statutory circular with highest precedence rank (5).
    """
    # Look up statutory wage ceiling rule ID for 2026
    rule = store.get_rule_as_of("statutory_wage_ceiling", event_date=date(2026, 10, 1))

    # Add a High Court stay/clarification
    override = JudicialOverrideRecord(
        override_id="88888888-8888-8888-8888-888888888888",
        target_rule_id=rule.rule_id,
        case_citation="High Court of Delhi - WP(C) No. 4921 of 2026",
        court_name="High Court of Delhi",
        jurisdiction_zone="DELHI_HC",
        override_type="stayed",
        override_value_numeric=1500000,  # Reverts to ₹15,000 pending final hearing in Delhi
        override_value_json=None,
        effective_from=date(2026, 9, 20),
        effective_to=date(2026, 12, 31),
        order_summary="Interim stay granted on notification enforcement within NCT of Delhi.",
        citation_url="https://delhihighcourt.nic.in/orders/4921_2026.pdf",
        doc_sha256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        is_active=True,
    )
    store.add_judicial_override(override)

    # In Delhi zone during stay window: returns overridden value ₹15,000 with rank 5
    delhi_result = store.get_rule_as_of(
        "statutory_wage_ceiling",
        event_date=date(2026, 10, 1),
        jurisdiction_zone="DELHI_HC",
    )
    assert delhi_result.is_judicial_override is True
    assert delhi_result.precedence_rank == 5
    assert delhi_result.value_numeric == 1500000
    assert "Judicial Override [STAYED]" in delhi_result.judicial_notes
    assert "High Court of Delhi" in delhi_result.judicial_notes

    # Outside Delhi zone: general national ₹25,000 applies
    national_result = store.get_rule_as_of(
        "statutory_wage_ceiling",
        event_date=date(2026, 10, 1),
        jurisdiction_zone="MUMBAI",
    )
    assert national_result.is_judicial_override is False
    assert national_result.value_numeric == 2500000
    assert national_result.precedence_rank == 10


# ============================================================================
# 5. STATUTORY ROUNDING POLICIES EXECUTION (Integer Paise)
# ============================================================================

def test_rounding_policies_execution(store: StatutoryStore):
    """
    Verifies that ECR, 7Q, and Admin Charges are rounded deterministically in integer paise.
    """
    # ECR: Round to nearest rupee (100 paise)
    # ₹1,250.40 = 125040 paise -> rounds down to ₹1,250.00 (125000 paise)
    assert store.apply_rounding("ECR", 125040) == 125000

    # ₹1,250.50 = 125050 paise -> rounds up to ₹1,251.00 (125100 paise)
    assert store.apply_rounding("ECR", 125050) == 125100

    # ₹1,250.89 = 125089 paise -> rounds up to ₹1,251.00 (125100 paise)
    assert store.apply_rounding("ECR", 125089) == 125100

    # ADMIN_CHARGES: Minimum charge floor is ₹750 (75000 paise)
    # If computed charge is ₹320 (32000 paise), floor enforces ₹750
    assert store.apply_rounding("ADMIN_CHARGES", 32000) == 75000
    # If computed charge is ₹920.40 (92040 paise), rounds to ₹920 (92000 paise)
    assert store.apply_rounding("ADMIN_CHARGES", 92040) == 92000


# ============================================================================
# 6. TAMPER-EVIDENT SHA256 HASH CHAIN INTEGRITY (rule_change_log)
# ============================================================================

def test_hash_chain_integrity_valid(store: StatutoryStore):
    """
    Verifies that the genesis block and all seeded rule promotions
    form an unbroken, cryptographically verifiable SHA256 hash chain.
    """
    valid, error_msg = store.verify_hash_chain_integrity()
    assert valid is True
    assert error_msg is None
    assert len(store.change_log) >= 10


def test_hash_chain_tamper_detection(store: StatutoryStore):
    """
    Simulates malicious or silent database tampering:
    Modifying any payload or approved_by attribute breaks the cryptographic chain.
    """
    # Tamper with an intermediate block
    store.change_log[3].payload["value_numeric"] = 99999999

    valid, error_msg = store.verify_hash_chain_integrity()
    assert valid is False
    assert "Tampered hash at sequence" in error_msg


# ============================================================================
# 7. CITATION ENVELOPE STANDARD SPECIFICATION TEST
# ============================================================================

def test_citation_envelope_format(store: StatutoryStore):
    """
    Verifies that every rule resolution returns the complete, standardized
    audit envelope required by non-negotiable rule #1.
    """
    envelope = store.get_rule_as_of("statutory_wage_ceiling", event_date=date(2026, 9, 20))
    d = envelope.to_dict()

    required_keys = {
        "rule_key", "value_numeric", "value_type", "value_json", "rule_id",
        "precedence_rank", "citation_url", "doc_sha256", "verbatim_quote",
        "evaluated_as_of_date", "effective_from", "effective_to",
        "is_retroactive", "retroactive_from", "is_judicial_override", "judicial_notes"
    }

    assert required_keys.issubset(d.keys())
    assert d["rule_key"] == "statutory_wage_ceiling"
    assert d["value_numeric"] == 2500000
    assert d["value_type"] == "integer_paise"
    assert d["doc_sha256"] == "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    assert d["precedence_rank"] == 10
    assert d["evaluated_as_of_date"] == "2026-09-20"
