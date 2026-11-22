"""
tests/gate/test_stage4_gate.py
Stage 4 Automated Regression & Consensus Gate Test Suite.
Verifies:
- Dual-Extractor Consensus (>= 0.98 vs Exception Escalation)
- Shadow-DB Regression Gate with Golden Test Matrix
- Tamper-Evident Hash-Chained Promotion in rule_change_log
- 24-Hour Canary Anomaly Detection and Autonomous Rollback
- Retroactive Dry-Run Impact Generation
- Exception-Only Review UI Queue & Single-Tap Resolution
"""

from datetime import date
import pytest

from db.statutory_store import build_seeded_statutory_store, StatutoryStore
from gate.consensus_evaluator import ConsensusEvaluator, GateAction
from gate.shadow_db_runner import ShadowDBRunner
from gate.canary_rollback import (
    CanaryMonitor,
    RollbackManager,
    RetroactiveDryRunGenerator,
)
from review_ui.app import ReviewUIManager, ExceptionStatus


@pytest.fixture
def store():
    return build_seeded_statutory_store()


# ============================================================================
# 1. DUAL-EXTRACTOR CONSENSUS & EXCEPTION GATING TESTS
# ============================================================================

def test_consensus_auto_promote_on_perfect_agreement():
    """
    When primary regex/table extractor and secondary LLM extractor agree 100%,
    consensus score >= 0.98 and action is AUTO_PROMOTE.
    """
    primary = {
        "rule_key": "statutory_wage_ceiling",
        "scope": {},
        "effective_from": "2026-09-17",
        "param_value": 2500000,
        "source_doc_sha256": "a" * 64,
        "is_retroactive": False,
    }
    secondary = {
        "rule_key": "statutory_wage_ceiling",
        "scope": {},
        "effective_from": "2026-09-17",
        "param_value": 2500000,
        "source_doc_sha256": "a" * 64,
        "is_retroactive": False,
    }

    decision = ConsensusEvaluator.evaluate(
        primary_diff=primary,
        secondary_diff=secondary,
        publication_date=date(2026, 9, 1),
    )
    assert decision.action == GateAction.AUTO_PROMOTE
    assert decision.consensus_score >= 0.98
    assert len(decision.escalation_reasons) == 0


def test_consensus_escalate_on_value_discrepancy():
    """
    When extractors disagree on numeric value (e.g., 2500000 vs 2100000),
    consensus score drops below 0.98 and action routes to ESCALATE_TO_HITL.
    """
    primary = {
        "rule_key": "statutory_wage_ceiling",
        "scope": {},
        "effective_from": "2026-09-17",
        "param_value": 2500000,
        "source_doc_sha256": "a" * 64,
    }
    secondary = {
        "rule_key": "statutory_wage_ceiling",
        "scope": {},
        "effective_from": "2026-09-17",
        "param_value": 2100000,  # Discrepancy
        "source_doc_sha256": "a" * 64,
    }

    decision = ConsensusEvaluator.evaluate(
        primary_diff=primary,
        secondary_diff=secondary,
    )
    assert decision.action == GateAction.ESCALATE_TO_HITL
    assert decision.consensus_score < 0.98
    assert any("CONSENSUS_BELOW_THRESHOLD" in r for r in decision.escalation_reasons)


def test_consensus_escalate_on_retroactive_effect():
    """
    Even with 100% extractor agreement, if effective_from precedes publication date,
    it must escalate to HITL as a retroactive rule with high blast radius.
    """
    primary = {
        "rule_key": "admin_charges_rate",
        "scope": {},
        "effective_from": "2025-01-01",  # Before pub date
        "param_value": 50,
        "source_doc_sha256": "b" * 64,
        "is_retroactive": True,
    }
    secondary = dict(primary)

    decision = ConsensusEvaluator.evaluate(
        primary_diff=primary,
        secondary_diff=secondary,
        publication_date=date(2025, 6, 1),
    )
    assert decision.action == GateAction.ESCALATE_TO_HITL
    assert decision.is_retroactive is True
    assert any("RETROACTIVE_RULE_DETECTED" in r for r in decision.escalation_reasons)


def test_consensus_escalate_on_court_stay():
    """
    When a judicial stay or court override is detected, escalate to HITL.
    """
    primary = {
        "rule_key": "edli_minimum_assurance_paise",
        "scope": {},
        "effective_from": "2026-01-01",
        "param_value": 25000000,
        "source_doc_sha256": "c" * 64,
    }
    secondary = dict(primary)

    decision = ConsensusEvaluator.evaluate(
        primary_diff=primary,
        secondary_diff=secondary,
        has_court_stay=True,
    )
    assert decision.action == GateAction.ESCALATE_TO_HITL
    assert decision.has_court_stay is True
    assert any("JUDICIAL_STAY" in r for r in decision.escalation_reasons)


# ============================================================================
# 2. SHADOW-DB REGRESSION & AUTO-PROMOTION TESTS
# ============================================================================

def test_shadow_db_auto_promote_passes_and_hashes(store: StatutoryStore):
    """
    A compliant candidate rule executes through the isolated shadow DB,
    passes all Stage 2 golden tests, and promotes to live store with hash-chain integrity.
    """
    initial_log_count = len(store.change_log)

    candidate = {
        "rule_key": "new_special_industry_allowance_cap",
        "scope": {"industry": "jute"},
        "effective_from": "2026-10-01",
        "effective_to": None,
        "param_value": 5000,
        "value_numeric": 5000,
        "value_type": "basis_points",
        "source_doc_sha256": "1" * 64,
        "citation_url": "https://epfindia.gov.in/circulars/special_industry_jute.pdf",
        "verbatim_quote": "Special allowance cap for jute industry",
        "precedence_rank": 20,
    }

    result = ShadowDBRunner.execute_gate_and_promote(
        live_store=store,
        candidate=candidate,
        proposed_by="diff_extractor",
        approved_by="shadow_gate_0615_ist",
        consensus_score=1.0,
    )

    assert result.success is True
    assert result.shadow_passed is True
    assert result.redis_cache_flushed is True
    assert len(store.change_log) == initial_log_count + 1

    # Verify live store hash-chain integrity is preserved
    is_valid, err = store.verify_hash_chain_integrity()
    assert is_valid is True
    assert err is None


def test_shadow_db_aborts_on_golden_regression_failure(store: StatutoryStore):
    """
    If a candidate rule breaks any Stage 2 golden scenario in the shadow DB,
    promotion is strictly aborted, live store is untouched, and failure is reported.
    """
    initial_rules_count = len(store.rules)
    initial_log_count = len(store.change_log)

    # Malicious/destructive candidate: setting wage ceiling to 100 paise in 2026
    # This will immediately break EMP-01 golden test!
    candidate = {
        "rule_key": "statutory_wage_ceiling",
        "scope": {},
        "effective_from": "2026-09-17",
        "effective_to": None,
        "param_value": 100,
        "value_numeric": 100,
        "value_type": "integer_paise",
        "source_doc_sha256": "f" * 64,
        "citation_url": "https://epfindia.gov.in/circulars/corrupt.pdf",
        "precedence_rank": 10,
    }

    result = ShadowDBRunner.execute_gate_and_promote(
        live_store=store,
        candidate=candidate,
    )

    # Must fail in shadow DB
    assert result.success is False
    assert result.shadow_passed is False
    assert "EMP-01" in result.failed_tests

    # Live store remains pristine
    assert len(store.rules) == initial_rules_count
    assert len(store.change_log) == initial_log_count


# ============================================================================
# 3. 24-HOUR CANARY ANOMALY DETECTION & AUTONOMOUS ROLLBACK
# ============================================================================

def test_canary_anomaly_and_auto_rollback(store: StatutoryStore):
    """
    Promote a rule, monitor for 24h, inject gap events exceeding threshold,
    and verify autonomous rollback restoring the superseded rule.
    """
    # 1. Promote a candidate
    candidate = {
        "rule_key": "test_canary_rule",
        "scope": {},
        "effective_from": "2026-10-01",
        "effective_to": None,
        "param_value": 850000,
        "value_numeric": 850000,
        "value_type": "integer_paise",
        "source_doc_sha256": "9" * 64,
    }
    res = ShadowDBRunner.execute_gate_and_promote(store, candidate)
    assert res.success is True
    promoted_id = res.rule_id

    # 2. Register with CanaryMonitor
    monitor = CanaryMonitor()
    monitor.register_promotion(rule_id=promoted_id, duration_hours=24)

    # 3. Inject telemetry (3 gap events)
    monitor.record_telemetry(promoted_id, "engine_gap_event")
    monitor.record_telemetry(promoted_id, "engine_gap_event")
    monitor.record_telemetry(promoted_id, "engine_gap_event")

    is_anomaly, reason = monitor.evaluate_health(promoted_id)
    assert is_anomaly is True
    assert "CANARY_ANOMALY" in reason

    # 4. Trigger auto-rollback
    rb_res = RollbackManager.execute_rollback(
        store=store,
        faulty_rule_id=promoted_id,
        reason=reason,
    )

    assert rb_res.success is True
    assert rb_res.redis_cache_flushed is True
    assert rb_res.alert_payload["severity"] == "CRITICAL"

    # Verify rule is rolled back in store
    rolled_back_rule = next(r for r in store.rules if r.rule_id == promoted_id)
    assert rolled_back_rule.status == "rolled_back"

    # Verify hash-chain remains valid after rollback entry
    is_valid, err = store.verify_hash_chain_integrity()
    assert is_valid is True
    assert err is None


# ============================================================================
# 4. RETROACTIVE DRY-RUN IMPACT GENERATOR
# ============================================================================

def test_retroactive_dry_run_generation():
    """
    Verifies that retroactive candidate rules produce an Affected Cases Report
    with calculated months, estimated cases, and signoff approval token.
    """
    candidate = {
        "rule_key": "retro_interest_rate",
        "scope": {},
        "effective_from": "2025-01-01",
        "retroactive_from": "2025-01-01",
        "param_value": 1200,
    }

    report = RetroactiveDryRunGenerator.generate_dry_run_report(
        candidate_diff=candidate,
        today_date=date(2026, 1, 1),
    )

    assert report.affected_months_count == 12
    assert report.estimated_affected_cases == 12 * 4500
    assert report.financial_impact_category == "HIGH_BLAST_RADIUS"
    assert len(report.approval_token) == 16
    assert report.requires_human_signoff is True


# ============================================================================
# 5. REVIEW UI EXCEPTION QUEUE & SINGLE-TAP HITL
# ============================================================================

def test_review_ui_queue_and_single_tap_approval(store: StatutoryStore):
    """
    Enqueues an exception item, verifies queue visibility,
    and executes single-tap approval with live store promotion.
    """
    ui_mgr = ReviewUIManager()

    candidate = {
        "rule_key": "special_tribunal_rate",
        "scope": {},
        "effective_from": "2026-11-01",
        "effective_to": None,
        "param_value": 750,
        "value_numeric": 750,
        "value_type": "basis_points",
        "source_doc_sha256": "e" * 64,
    }

    # Enqueue item
    item = ui_mgr.enqueue_exception(
        rule_key=candidate["rule_key"],
        reasons=["LOW_OCR_CONFIDENCE: 0.78 < 0.85"],
        candidate_diff=candidate,
    )
    assert item.status == ExceptionStatus.PENDING

    # Check pending items
    pending = ui_mgr.get_pending_items()
    assert len(pending) == 1
    assert pending[0].item_id == item.item_id

    # Single-tap approve
    res = ui_mgr.resolve_item(
        item_id=item.item_id,
        decision="APPROVE",
        reviewer="senior_compliance_officer",
        notes="Verified manually against official Gazette physical copy.",
        live_store=store,
    )

    assert res["status"] == "APPROVED"
    assert res["promotion"]["success"] is True
    assert item.status == ExceptionStatus.APPROVED
    assert len(ui_mgr.get_pending_items()) == 0
