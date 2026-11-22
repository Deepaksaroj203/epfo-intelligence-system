"""
ingest/workers/gap_and_inbound.py
Event-Driven Inbound & Self-Enhancement Worker.
Consumes Stage 2 engine_gap_event logs, compliance email webhooks,
and in-app feedback flags to seed candidate golden tests and trigger instant Tier 1 verification sweeps.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


class GapAndInboundWorker:
    """
    Orchestrates the self-enhancement feedback loop between Stage 2, Stage 3, and Stage 4.
    """

    def __init__(self):
        self.pending_gap_tickets: List[Dict[str, Any]] = []
        self.candidate_golden_tests: List[Dict[str, Any]] = []

    def consume_engine_gap_event(
        self,
        source_side: str,
        error_code: str,
        context: Dict[str, Any],
        proposed_solution: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Receives an unhandled gap event from Stage 2 and seeds a candidate golden test.
        """
        ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"

        ticket = {
            "ticket_id": ticket_id,
            "source_side": source_side,
            "error_code": error_code,
            "context": context,
            "proposed_solution": proposed_solution,
            "status": "QUEUED_FOR_STAGE_4",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.pending_gap_tickets.append(ticket)

        # Seed candidate golden test
        golden_test_seed = {
            "test_id": f"AUTO-GEN-{error_code}",
            "side": source_side,
            "scenario": f"Automatic regression for unhandled error code: {error_code}",
            "context": context,
            "expected_action": proposed_solution or "FLAG_FOR_REVIEW",
        }
        self.candidate_golden_tests.append(golden_test_seed)

        return ticket

    def consume_feedback_flag(
        self,
        rule_id: str,
        notes: str,
        circular_ref: Optional[str] = None,
        reporter_role: str = "HR_PRACTITIONER",
    ) -> Dict[str, Any]:
        """
        Processes in-app /v1/feedback/flag submissions, triggering an immediate Tier 1 crawl.
        """
        flag_id = f"FLAG-{uuid.uuid4().hex[:8].upper()}"
        return {
            "flag_id": flag_id,
            "rule_id": rule_id,
            "notes": notes,
            "circular_ref": circular_ref,
            "reporter_role": reporter_role,
            "dispatch_action": "TRIGGER_TIER_1_VERIFICATION_CRAWL",
            "status": "VERIFICATION_DISPATCHED",
        }
