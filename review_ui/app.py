"""
review_ui/app.py
Stage 4 Exception-Only Review UI Backend (FastAPI).
Lightweight exception queue strictly for the <10% updates that require human oversight:
- Low-confidence consensus (< 0.98)
- Scanned illegible OCR
- High-blast-radius retroactive changes (with dry-run impact report)
- Court stay / judicial override interceptions
- Shadow-DB golden regression failures
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from gate.shadow_db_runner import ShadowDBRunner
from db.statutory_store import StatutoryStore


class ExceptionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ReviewQueueItem:
    item_id: str
    rule_key: str
    reasons: List[str]
    candidate_diff: Dict[str, Any]
    dry_run_report: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ExceptionStatus = ExceptionStatus.PENDING
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    decision_notes: Optional[str] = None


class ReviewUIManager:
    """
    In-memory / persistent manager for the exception queue.
    """

    def __init__(self):
        self.queue: Dict[str, ReviewQueueItem] = {}

    def enqueue_exception(
        self,
        rule_key: str,
        reasons: List[str],
        candidate_diff: Dict[str, Any],
        dry_run_report: Optional[Dict[str, Any]] = None,
    ) -> ReviewQueueItem:
        item_id = f"REV-{uuid.uuid4().hex[:8].upper()}"
        item = ReviewQueueItem(
            item_id=item_id,
            rule_key=rule_key,
            reasons=reasons,
            candidate_diff=candidate_diff,
            dry_run_report=dry_run_report,
        )
        self.queue[item_id] = item
        return item

    def get_pending_items(self) -> List[ReviewQueueItem]:
        return [item for item in self.queue.values() if item.status == ExceptionStatus.PENDING]

    def resolve_item(
        self,
        item_id: str,
        decision: str,  # "APPROVE" | "REJECT"
        reviewer: str,
        notes: str = "",
        live_store: Optional[StatutoryStore] = None,
    ) -> Dict[str, Any]:
        if item_id not in self.queue:
            raise KeyError(f"Review item {item_id} not found.")

        item = self.queue[item_id]
        if item.status != ExceptionStatus.PENDING:
            raise ValueError(f"Review item {item_id} already resolved as {item.status}.")

        now_str = datetime.now(timezone.utc).isoformat()

        if decision == "APPROVE":
            item.status = ExceptionStatus.APPROVED
            item.resolved_by = reviewer
            item.resolved_at = now_str
            item.decision_notes = notes

            # If store provided, execute promotion
            promotion_result = None
            if live_store:
                promotion_result = ShadowDBRunner.execute_gate_and_promote(
                    live_store=live_store,
                    candidate=item.candidate_diff,
                    proposed_by="review_ui_hitl",
                    approved_by=reviewer,
                    consensus_score=1.0,
                )

            return {
                "status": "APPROVED",
                "item_id": item_id,
                "promotion": promotion_result.__dict__ if promotion_result else None,
            }

        elif decision == "REJECT":
            item.status = ExceptionStatus.REJECTED
            item.resolved_by = reviewer
            item.resolved_at = now_str
            item.decision_notes = notes
            return {
                "status": "REJECTED",
                "item_id": item_id,
                "reason": notes,
            }
        else:
            raise ValueError(f"Invalid decision: {decision}. Must be 'APPROVE' or 'REJECT'.")
