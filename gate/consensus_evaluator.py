"""
gate/consensus_evaluator.py
Stage 4 Dual-Extractor Consensus & Autonomous Exception Gate.
Evaluates candidate rule diffs from Stage 3 by comparing deterministic
table/regex parser extraction against sandboxed LLM extraction.
Scores consensus (>= 0.98 threshold) and gates auto-promotion vs exception-only HITL.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class GateAction(str, Enum):
    AUTO_PROMOTE = "AUTO_PROMOTE"
    ESCALATE_TO_HITL = "ESCALATE_TO_HITL"


@dataclass
class EvaluationDecision:
    action: GateAction
    consensus_score: float
    field_matches: Dict[str, bool]
    is_retroactive: bool
    has_court_stay: bool
    escalation_reasons: List[str] = field(default_factory=list)
    affected_cases_count: Optional[int] = None


class ConsensusEvaluator:
    """
    Evaluates agreement between two independent extractors:
    1. Deterministic Rule/Table Parser (e.g., pdfplumber tables or regex anchors)
    2. Sandboxed LLM Diff Extractor
    """

    CONSENSUS_THRESHOLD = 0.98

    @classmethod
    def evaluate(
        cls,
        primary_diff: Dict[str, Any],
        secondary_diff: Dict[str, Any],
        publication_date: Optional[date] = None,
        has_court_stay: bool = False,
        ocr_confidence: float = 1.0,
    ) -> EvaluationDecision:
        field_matches = {}
        escalation_reasons = []

        # 1. Compare rule_key (weight: 0.25)
        rk1 = primary_diff.get("rule_key")
        rk2 = secondary_diff.get("rule_key")
        field_matches["rule_key"] = (rk1 == rk2 and rk1 is not None)

        # 2. Compare scope (weight: 0.15)
        sc1 = primary_diff.get("scope")
        sc2 = secondary_diff.get("scope")
        field_matches["scope"] = (sc1 == sc2 and sc1 is not None)

        # 3. Compare effective_from (weight: 0.20)
        ef1 = str(primary_diff.get("effective_from"))
        ef2 = str(secondary_diff.get("effective_from"))
        field_matches["effective_from"] = (ef1 == ef2 and ef1 != "None")

        # 4. Compare param_value (weight: 0.30)
        # Deep compare dicts or direct types
        pv1 = primary_diff.get("param_value")
        pv2 = secondary_diff.get("param_value")
        field_matches["param_value"] = (pv1 == pv2 and pv1 is not None)

        # 5. Compare doc_sha256 & provenance (weight: 0.10)
        sha1 = primary_diff.get("source_doc_sha256")
        sha2 = secondary_diff.get("source_doc_sha256")
        field_matches["provenance"] = (sha1 == sha2 and sha1 is not None)

        # Calculate weighted consensus score
        weights = {
            "rule_key": 0.25,
            "scope": 0.15,
            "effective_from": 0.20,
            "param_value": 0.30,
            "provenance": 0.10,
        }
        consensus_score = sum(weights[k] for k, matched in field_matches.items() if matched)

        # Check retroactivity
        is_retro = bool(primary_diff.get("is_retroactive", False) or secondary_diff.get("is_retroactive", False))
        if publication_date:
            eff_date = primary_diff.get("effective_from")
            if isinstance(eff_date, str):
                eff_date = date.fromisoformat(eff_date)
            if isinstance(eff_date, date) and eff_date < publication_date:
                is_retro = True

        # Check triggers for exception escalation
        if ocr_confidence < 0.85:
            escalation_reasons.append(f"LOW_OCR_CONFIDENCE: {ocr_confidence:.2f} < 0.85")

        if consensus_score < cls.CONSENSUS_THRESHOLD:
            escalation_reasons.append(
                f"CONSENSUS_BELOW_THRESHOLD: {consensus_score:.4f} < {cls.CONSENSUS_THRESHOLD}"
            )

        if is_retro:
            escalation_reasons.append(
                f"RETROACTIVE_RULE_DETECTED: effective_from precedes publication date or is_retroactive is set"
            )

        if has_court_stay:
            escalation_reasons.append("JUDICIAL_STAY_OR_OVERRIDE_ACTIVE: requires judicial compliance review")

        action = GateAction.AUTO_PROMOTE if not escalation_reasons else GateAction.ESCALATE_TO_HITL

        return EvaluationDecision(
            action=action,
            consensus_score=round(consensus_score, 4),
            field_matches=field_matches,
            is_retroactive=is_retro,
            has_court_stay=has_court_stay,
            escalation_reasons=escalation_reasons,
        )
