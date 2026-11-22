"""
engines/member/grievance_router.py
Member-side deterministic grievance analysis and EPFiGMS category routing engine.
Implements:
- SLA norm breach detection (20-day claim settlement charter)
- False claim closure detection without speaking order
- Employer attestation deadlock routing to CAIU inspection
- Tier 4 troubleshooting KB enrichment
"""

from datetime import date
from typing import Any, Dict, List, Optional
from db.statutory_store import StatutoryStore
from engines.common import EngineResult


def evaluate_grievance_route(
    days_pending: int,
    issue_type: str,  # "CLAIM_DELAY", "FALSE_CLOSURE", "EMPLOYER_DEADLOCK", "PASSBOOK_ERROR"
    claim_id: Optional[str] = None,
    rejection_reason_text: Optional[str] = None,
    store: Optional[StatutoryStore] = None,
    event_date: Optional[date] = None,
) -> EngineResult:
    """
    Analyzes member grievance facts, detects statutory/charter norm violations,
    and returns exact EPFiGMS classification, escalation tiers, and troubleshooting steps.
    """
    eval_date = event_date or date.today()
    working_steps: List[str] = []
    blockers: List[str] = []
    troubleshooting_tips: List[Dict[str, Any]] = []

    epfigms_category = "GENERAL_GRIEVANCE"
    escalation_level = "LEVEL_1_REGIONAL_OFFICE"
    sla_breached = False

    # 1. Claim Delay Evaluation (EPFO Citizen Charter SLA: 20 Days)
    if issue_type == "CLAIM_DELAY":
        if days_pending > 20:
            sla_breached = True
            working_steps.append(
                f"SLA Norm Breach Detected: Claim pending for {days_pending} days. "
                f"Statutory limit under EPFO Citizen's Charter & Head Office Circular is 20 days."
            )
            if days_pending > 30:
                escalation_level = "LEVEL_2_ZONAL_OFFICE"
                epfigms_category = "Grievance - Delay in Settlement of Claim (Exceeded 30 Days)"
            else:
                epfigms_category = "Delay in Settlement of Claim (Form 19/10C/31)"
        else:
            working_steps.append(f"Claim pending for {days_pending} days (within standard 20-day turnaround SLA).")
            epfigms_category = "Inquiry - Status of Claim"

    # 2. False Claim Closure Without Reasoned Speaking Order
    elif issue_type == "FALSE_CLOSURE":
        reason = (rejection_reason_text or "").lower()
        opaque_reasons = ["technical error", "rejected", "contact office", "clarification required", "invalid"]
        is_opaque = any(op in reason for op in opaque_reasons) or len(reason.strip()) < 10

        if is_opaque:
            working_steps.append(
                f"Speaking Order Violation: Rejection remark '{rejection_reason_text}' is vague/opaque. "
                f"Under Head Office Circular No. WSU/2022/ClaimRejection/561, Field Offices MUST issue a detailed, "
                f"reasoned speaking order specifying exact missing documents and remediations."
            )
            epfigms_category = "Grievance - Improper / Unreasoned Rejection of Claim"
            escalation_level = "LEVEL_2_REGIONAL_PF_COMMISSIONER"
            troubleshooting_tips.append({
                "code": "SPEAKING_ORDER_MANDATE",
                "message": "Cite HO Circular WSU/2022 on EPFiGMS. Demand exact document requirement or re-opening of claim.",
                "link": "https://epfigms.gov.in"
            })
        else:
            working_steps.append(f"Claim closure reason provided: '{rejection_reason_text}'.")
            epfigms_category = "Grievance - Disputed Rejection"

    # 3. Employer Attestation Deadlock (Employer refuses to sign KYC / Joint Declaration)
    elif issue_type == "EMPLOYER_DEADLOCK":
        working_steps.append(
            "Employer Attestation Deadlock Detected: Establishment is unresponsive or refusing statutory attestation. "
            "Under Section 7A & Compliance Manual, employer non-cooperation is actionable. "
            "Routing to Central Analysis & Intelligence Unit (CAIU) / Squad Inspection wing."
        )
        epfigms_category = "Employer Non-Compliance - Refusal of KYC Attestation / Joint Declaration"
        escalation_level = "LEVEL_2_ENFORCEMENT_WING"
        troubleshooting_tips.append({
            "code": "CAIU_INSPECTION_ESCALATION",
            "message": "Submit registered representation to RPFC-I with proof of employment (appointment letter, payslips, Form 16).",
            "link": "https://www.epfindia.gov.in"
        })

    return EngineResult(
        value={
            "epfigms_category": epfigms_category,
            "escalation_level": escalation_level,
            "sla_breached": sla_breached,
            "days_pending": days_pending,
            "portal_url": "https://epfigms.gov.in",
        },
        working_steps=working_steps,
        blockers=blockers,
        approval_tier="GRIEVANCE_ESCALATION_GATE",
        judicial_notes=None,
        troubleshooting_tips=troubleshooting_tips,
        rule_id="RULE_EPFIGMS_SLA_CHARTER",
        citation_url="https://epfigms.gov.in",
        doc_sha256="ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d",
        evaluated_as_of_date=str(eval_date),
        metadata={
            "issue_type": issue_type,
            "claim_id": claim_id,
        },
    )
