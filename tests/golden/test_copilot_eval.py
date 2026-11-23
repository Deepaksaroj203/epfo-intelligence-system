"""
tests/golden/test_copilot_eval.py
Autonomous Agent Evaluation & Benchmark Suite for EPFO Intelligence Copilot.
Directly implements principles from 'agent-evaluation', 'rag-implementation',
and 'test-driven-development'.
"""

import pytest
from datetime import date
from db.statutory_store import build_seeded_statutory_store
from api.rag_engine import PrecedentsStore, TroubleshootingKB
from api.copilot import EPFOCopilot


@pytest.fixture(scope="module")
def copilot():
    store = build_seeded_statutory_store()
    precedents = PrecedentsStore()
    kb = TroubleshootingKB()
    return EPFOCopilot(store, precedents, kb)


class TestCopilotStatutoryEvaluation:
    """Benchmark tests evaluating conversational statutory accuracy and citation locks."""

    def test_eval_wage_ceiling_benchmark(self, copilot):
        res = copilot.answer_query("What is the current wage ceiling and what is the new appointed ceiling for 2026?")
        assert res["intent"] == "WAGE_CEILING"
        assert "15,000" in res["answer_markdown"]
        assert "25,000" in res["answer_markdown"]
        assert len(res["citations"]) >= 2
        for cite in res["citations"]:
            assert cite["doc_sha256"] is not None
            assert len(cite["doc_sha256"]) == 64

    def test_eval_7q_14b_penalties_benchmark(self, copilot):
        res = copilot.answer_query("Calculate 7Q interest and 14B damages for delay of 75 days on 2,50,000 dues")
        assert res["intent"] == "PENALTIES_7Q_14B"
        assert "Section 7Q" in res["answer_markdown"]
        assert "Section 14B" in res["answer_markdown"]
        assert "CGIT Tribunal Appeal Pre-Deposit (Section 7O)" in res["answer_markdown"]
        assert len(res["citations"]) > 0

    def test_eval_50_percent_allowance_add_back_benchmark(self, copilot):
        res = copilot.answer_query("Employee has gross salary 40,000 and basic 12,000. Calculate PF contribution and 50% allowance cap")
        assert res["intent"] == "50_PERCENT_ALLOWANCE"
        assert "50% Threshold" in res["answer_markdown"] or "Excess Added Back" in res["answer_markdown"]
        assert "calculation_summary" in res

    def test_eval_pension_edli_benchmark(self, copilot):
        res = copilot.answer_query("Can I get EPS pension with 6 years of service or Form 10C withdrawal benefit?")
        assert res["intent"] == "PENSION_EPS_EDLI"
        assert "10-Year Service Gate" in res["answer_markdown"] or "10 Years" in res["answer_markdown"]
        assert "Form 10C" in res["answer_markdown"]

    def test_eval_rejection_troubleshooting_benchmark(self, copilot):
        res = copilot.answer_query("My Form 19 was rejected due to wage month discrepancy and missing father name in KYC")
        assert res["intent"] == "CLAIM_REJECTION_TROUBLESHOOT"
        assert len(res["actionable_steps"]) > 0
        assert "speaking order" in res["answer_markdown"].lower() or "grievance" in res["answer_markdown"].lower()

    def test_eval_precedents_citation_benchmark(self, copilot):
        res = copilot.answer_query("Show me Supreme Court ruling on basic wage and allowances Vivek Mandir or Vivekananda")
        assert res["intent"] == "PRECEDENTS_CASE_LAW"
        assert len(res["citations"]) > 0
        # Check PII-compliant precedent retrieval or key holding on basic wages
        matched_any = any(
            "Sunil Kumar" in (c.get("case_title") or "") or
            "basic wages" in (c.get("key_holding") or "").lower() or
            "2(b)" in (c.get("key_holding") or "")
            for c in res["citations"]
        )
        assert matched_any
