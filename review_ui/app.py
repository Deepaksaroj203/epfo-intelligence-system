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


# FastAPI application instance for Review UI container / dashboard
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="EPFO Stage 4 Exception Review Dashboard", docs_url="/docs")
ui_manager = ReviewUIManager()


@app.get("/health")
def review_health():
    return {"status": "HEALTHY", "service": "review_ui"}


@app.get("/review/queue")
def get_queue():
    return ui_manager.get_pending_items()


@app.get("/review/{item_id}")
def get_item(item_id: str):
    if item_id not in ui_manager.queue:
        raise HTTPException(status_code=404, detail="Item not found")
    return ui_manager.queue[item_id]


@app.post("/review/{item_id}/decision")
def make_decision(item_id: str, decision: str, reviewer: str = "compliance_officer", notes: str = ""):
    return ui_manager.resolve_item(item_id=item_id, decision=decision, reviewer=reviewer, notes=notes)


@app.get("/", response_class=HTMLResponse)
def index_ui():
    items = ui_manager.get_pending_items()
    rows = "".join(f"<tr><td>{it.item_id}</td><td>{it.rule_key}</td><td>{', '.join(it.reasons)}</td></tr>" for it in items)
    return f"""
    <html>
      <head>
        <title>EPFO Exception Review UI</title>
        <style>
          body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
          h2 {{ color: #38bdf8; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
          th, td {{ border: 1px solid #334155; padding: 12px; text-align: left; }}
          th {{ background: #1e293b; color: #94a3b8; }}
          tr:hover {{ background: #1e293b; }}
        </style>
      </head>
      <body>
        <h2>EPFO Statutory Intelligence — Stage 4 Exception Review Queue</h2>
        <p>Pending human escalation items (Threshold: consensus &lt; 0.98, judicial stay, or retroactive diff):</p>
        <table>
          <tr><th>Item ID</th><th>Rule Key</th><th>Escalation Reasons</th></tr>
          {rows or '<tr><td colspan="3" style="text-align:center; color:#94a3b8;">Zero pending exception items. Autonomous consensus operating smoothly.</td></tr>'}
        </table>
      </body>
    </html>
    """

