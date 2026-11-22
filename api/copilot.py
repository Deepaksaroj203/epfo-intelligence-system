"""
api/copilot.py
Authoritative Natural Language EPFO Copilot Orchestrator.
Powers the "Ask Anything about EPFO" conversational interface, Telegram Bot,
and Social AI automated briefing engine.
Transforms natural user queries into deterministic Stage 1-5 engine calls,
returning plain-language legal answers locked to statutory citations.
"""

from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from api.rag_engine import PrecedentsStore, TroubleshootingKB
from db.statutory_store import StatutoryStore
from engines.common import EmployerCaseInput, MemberCaseInput
from engines.employer.penalties_appeals import evaluate_penalties_and_appeals
from engines.employer.wage_contributions import evaluate_wage_contributions
from engines.member.claims_eligibility import evaluate_claims_eligibility
from engines.member.legal_drafter import LegalDrafter
from engines.member.pension_edli import evaluate_pension_and_edli
from engines.member.portal_preflight import evaluate_portal_preflight


class EPFOCopilot:
    """
    Intelligent conversational query engine for EPFO Statutory Rules & Cases.
    """

    def __init__(
        self,
        store: StatutoryStore,
        precedents: PrecedentsStore,
        kb: TroubleshootingKB,
    ):
        self.store = store
        self.precedents = precedents
        self.kb = kb

    def answer_query(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower().strip()

        # 1. Intent: 7Q Interest & 14B Damages / Penalties / Section 7O Appeal
        if any(w in q_lower for w in ["7q", "14b", "penalty", "penalties", "damages", "delay", "late payment", "7o", "appeal deposit"]):
            return self._handle_penalties(query)

        # 2. Intent: Wage Ceiling
        if any(w in q_lower for w in ["wage ceiling", "statutory ceiling", "salary limit", "wage limit", "ceiling hike", "25000 ceiling", "15000 ceiling"]):
            return self._handle_wage_ceiling(q_lower)

        # 3. Intent: Pension / EPS / EDLI / Withdrawal
        if any(w in q_lower for w in ["pension", "eps", "edli", "form 10c", "withdrawal benefit", "10 years service"]):
            return self._handle_pension_edli(query)

        # 4. Intent: Portal Rejection / Form 19 / Troubleshooting
        if any(w in q_lower for w in ["reject", "rejected", "rejection", "form 19", "dsc", "kyc", "wage month", "speaking order"]):
            return self._handle_claim_troubleshooting(query)

        # 5. Intent: Case Laws / Judgments / Precedents
        if any(w in q_lower for w in ["court", "judgment", "ruling", "supreme court", "high court", "cgit", "tribunal", "case law"]):
            return self._handle_precedents(query)

        # 6. Intent: 50% Allowance Cap Add-Back & Salary Contribution Calculations
        if any(w in q_lower for w in ["calculate", "50%", "allowance cap", "add back", "wage contribution", "pf contribution", "allowances exceed", "basic salary"]):
            return self._handle_50_percent_allowance(query)

        # 7. Fallback: General Semantic & Knowledge Search
        return self._handle_general_search(query)

    def _handle_wage_ceiling(self, query: str) -> Dict[str, Any]:
        today = date.today()
        current_envelope = self.store.get_rule_as_of("statutory_wage_ceiling", {}, today)
        future_envelope = self.store.get_rule_as_of("statutory_wage_ceiling", {}, date(2026, 9, 17))
        hist_envelope = self.store.get_rule_as_of("statutory_wage_ceiling", {}, date(2014, 8, 31))

        text = (
            f"### Statutory EPFO Wage Ceiling Regime\n\n"
            f"1. **Pre-September 2014**: ₹6,500/month (650,000 paise) per G.S.R. 399(E).\n"
            f"2. **Current Active Regime**: **₹15,000/month** (1,500,000 paise) per G.S.R. 608(E) dated 19-Aug-2014.\n"
            f"3. **Appointed 2026 Revision**: **₹25,000/month** (2,500,000 paise) appointed with the EPF/EPS/EDLI Schemes 2026.\n\n"
            f"**Statutory Effect**:\n"
            f"- For employees joining with basic wages > wage ceiling, membership is optional (exempted if not enrolled earlier).\n"
            f"- Employer EPS contribution (8.33%) is strictly capped at the statutory wage ceiling unless Para 11(4) joint option applies."
        )

        return {
            "intent": "WAGE_CEILING",
            "answer_markdown": text,
            "citations": [
                {"title": "G.S.R. 608(E) (₹15,000 ceiling)", "url": current_envelope.citation_url, "doc_sha256": current_envelope.doc_sha256},
                {"title": "S.O. 5109(E) (₹25,000 appointed ceiling)", "url": future_envelope.citation_url, "doc_sha256": future_envelope.doc_sha256},
            ],
            "actionable_steps": [
                "Verify whether employee enrolled in EPF before crossing the wage ceiling.",
                "Ensure EPS 8.33% is capped to statutory ceiling to avoid ECR rejection."
            ]
        }

    def _handle_50_percent_allowance(self, query: str) -> Dict[str, Any]:
        # Extract figures if present (strip commas first)
        clean_q = re.sub(r",", "", query)
        all_nums = [int(n) for n in re.findall(r"\b\d+\b", clean_q) if int(n) >= 100]
        basic = all_nums[0] if len(all_nums) > 0 else 20000
        allowances = all_nums[1] if len(all_nums) > 1 else 30000
        gross = basic + allowances

        case = EmployerCaseInput(
            employee_count=25,
            branch_count=1,
            wage_month=date.today(),
            due_date=date.today(),
            payment_date=date.today(),
            gross_wages_paise=gross * 100,
            basic_wages_paise=basic * 100,
            excluded_allowances_paise=allowances * 100,
        )
        res = evaluate_wage_contributions(case, self.store)
        val = res.value

        excess_added = val["excess_allowances_added_back_paise"] / 100
        statutory_wage = val["adjusted_statutory_wage_paise"] / 100
        ee_pf = val["ee_epf_paise"] / 100
        er_eps = val["er_eps_paise"] / 100
        er_diff = val.get("er_epf_diff_paise", val.get("er_epf_paise", 0)) / 100

        text = (
            f"### The 50% Allowance Cap Rule (Section 2(b) & Code on Social Security)\n\n"
            f"Under the statutory wage definition, if excluded allowances (HRA, travel, special allowance, etc.) "
            f"exceed **50% of total gross remuneration**, the excess amount **MUST be added back** to Basic Wages for PF calculation.\n\n"
            f"**Calculation Breakdown for Gross ₹{gross:,.2f}**:\n"
            f"- Basic Wages: ₹{basic:,.2f}\n"
            f"- Excluded Allowances: ₹{allowances:,.2f} ({(allowances/gross)*100:.1f}% of gross)\n"
            f"- 50% Threshold: ₹{gross/2:,.2f}\n"
            f"- **Excess Added Back**: **₹{excess_added:,.2f}**\n"
            f"- **Adjusted PF Statutory Wage**: **₹{statutory_wage:,.2f}**\n\n"
            f"**Statutory Contributions**:\n"
            f"- Employee EPF (12%): ₹{ee_pf:,.2f}\n"
            f"- Employer EPS (8.33% capped): ₹{er_eps:,.2f}\n"
            f"- Employer EPF Difference (3.67%): ₹{er_diff:,.2f}"
        )

        return {
            "intent": "50_PERCENT_ALLOWANCE",
            "answer_markdown": text,
            "citations": [
                {"title": "Section 2(b) & Section 6, EPF Act 1952", "url": res.citation_url, "doc_sha256": res.doc_sha256}
            ],
            "calculation_summary": val,
        }

    def _handle_penalties(self, query: str) -> Dict[str, Any]:
        clean_q = re.sub(r",", "", query)
        all_nums = [int(n) for n in re.findall(r"\b\d+\b", clean_q)]

        arrears = 100000
        delay_days = 60

        # Discern large principal arrears vs delay days
        large_nums = [n for n in all_nums if n >= 1000]
        small_nums = [n for n in all_nums if n < 1000]

        if large_nums:
            arrears = large_nums[0]
        if small_nums:
            delay_days = small_nums[0]
        elif len(all_nums) > 1 and not small_nums:
            delay_days = all_nums[1]

        case = EmployerCaseInput(
            employee_count=50,
            branch_count=1,
            wage_month=date(2026, 1, 1),
            due_date=date(2026, 2, 15),
            payment_date=date(2026, 2, 15) + __import__("datetime").timedelta(days=delay_days),
            gross_wages_paise=arrears * 100,
            basic_wages_paise=arrears * 100,
            excluded_allowances_paise=0,
            remittance_amount_paise=arrears * 100,
        )
        res = evaluate_penalties_and_appeals(case, self.store)
        val = res.value

        int_7q = val["interest_7q_paise"] / 100
        dam_14b = val["damages_14b_paise"] / 100
        total_pen = val["total_statutory_penalty_paise"] / 100
        total_assessed = val["total_assessed_determination_paise"] / 100
        deposit_7o = val["appeal_deposit_7o_paise"] / 100

        text = (
            f"### Late Remittance Penalties & Appeal Pre-Deposit (Delayed by {delay_days} days)\n\n"
            f"**Assessed Arrears**: ₹{arrears:,.2f}\n\n"
            f"1. **Section 7Q Simple Interest (12.00% per annum)**:\n"
            f"   - Formula: `(Arrears × 12% × {delay_days}) / 365`\n"
            f"   - **Interest Due**: **₹{int_7q:,.2f}**\n\n"
            f"2. **Section 14B Penal Damages**:\n"
            f"   - Rate: `{val['damage_rate_applied']}`\n"
            f"   - **Damages Due**: **₹{dam_14b:,.2f}**\n\n"
            f"3. **Total Determined Statutory Liability**: **₹{total_assessed:,.2f}**\n\n"
            f"4. **CGIT Tribunal Appeal Pre-Deposit (Section 7O)**:\n"
            f"   - Under Section 7O, to appeal before the CGIT Tribunal, the employer **MUST pre-deposit exactly 25.00%** of total assessed liability.\n"
            f"   - **Mandatory Pre-Deposit**: **₹{deposit_7o:,.2f}**"
        )

        return {
            "intent": "PENALTIES_7Q_14B",
            "answer_markdown": text,
            "citations": [
                {"title": "Section 7Q (12% Simple Interest)", "url": res.citation_url, "doc_sha256": res.doc_sha256},
                {"title": "Section 14B & Section 7O (25% Pre-Deposit)", "url": res.citation_url, "doc_sha256": res.doc_sha256},
            ],
            "appeal_guidance": "You can auto-generate a citation-locked CGIT Appeal Memorandum via POST /v1/legal/draft/cgit-appeal."
        }

    def _handle_pension_edli(self, query: str) -> Dict[str, Any]:
        text = (
            f"### Employees' Pension Scheme (EPS 1995) & EDLI Entitlements\n\n"
            f"1. **10-Year Service Gate**:\n"
            f"   - **< 10 Years Service**: Eligible for **EPS Withdrawal Benefit** (Scheme Certificate or cash withdrawal via Form 10C).\n"
            f"   - **>= 10 Years (3,600 Contributory Days)**: Eligible for **Monthly Superannuation Pension** at age 58 (or Early Reduced Pension from age 50).\n\n"
            f"2. **Employer Contribution Default Safeguard**:\n"
            f"   - If employer defaults in depositing contributions, the defaulted months are excluded from pensionable service without forfeiting the member's underlying terminal rights.\n\n"
            f"3. **EDLI Life Insurance Assurance**:\n"
            f"   - Assurance benefit = `(35 × Average Wages of last 12 months) + 50% of balance (max ₹1.75L)`.\n"
            f"   - **Minimum Assurance**: ₹2,50,000 | **Maximum Assurance**: ₹7,00,000."
        )
        return {
            "intent": "PENSION_EPS_EDLI",
            "answer_markdown": text,
            "citations": [
                {"title": "Employees' Pension Scheme, 1995 (Paras 10, 12, 14)", "url": "https://epfindia.gov.in/rules/eps.pdf"},
                {"title": "EDLI Scheme, 1976 (Para 22)", "url": "https://epfindia.gov.in/rules/edli.pdf"},
            ],
        }

    def _handle_claim_troubleshooting(self, query: str) -> Dict[str, Any]:
        # Detect common error patterns
        matched_sol = None
        if "wage month" in query or "completed" in query or "5th" in query:
            matched_sol = self.kb.lookup_solution("ERR_502_WAGE_MONTH")
        elif "dsc" in query or "employer" in query or "attestation" in query:
            matched_sol = self.kb.lookup_solution("ERR_DSC_NOT_REGISTERED")
        elif "bank" in query:
            matched_sol = self.kb.lookup_solution("ERR_BANK_KYC_PENDING")

        if matched_sol:
            steps_str = "\n".join(f"   {i+1}. {s}" for i, s in enumerate(matched_sol["workaround_steps"]))
            text = (
                f"### Resolution for Claim Issue: `{matched_sol['error_code']}`\n\n"
                f"**Root Cause**: {matched_sol['root_cause']}\n\n"
                f"**Actionable Steps**:\n{steps_str}\n\n"
                f"**Legal Protection**:\n"
                f"Under EPFO Circular dated 12-Mar-2024, field offices are strictly prohibited from rejecting claims without issuing a reasoned speaking order. If arbitrary rejection persists, generate a formal EPFiGMS grievance."
            )
            return {
                "intent": "CLAIM_REJECTION_TROUBLESHOOT",
                "answer_markdown": text,
                "solution": matched_sol,
                "actionable_steps": matched_sol["workaround_steps"],
            }

        # Closed establishment fallback
        text = (
            f"### Closed Establishment Fallback Pathway (Form 19 / 10C)\n\n"
            f"If your previous employer establishment has closed down, become insolvent, or the employer refuses to approve DSC:\n"
            f"1. You are legally **exempt from employer DSC attestation**.\n"
            f"2. You can submit physical Form 19/10C attested by an authorized authority: **Bank Manager**, Gazetted Officer, or Magistrate.\n"
            f"3. EPFO field offices are mandated to process the claim within 20 days upon verification of Bank KYC."
        )
        return {
            "intent": "CLOSED_ESTABLISHMENT_FALLBACK",
            "answer_markdown": text,
            "citations": [
                {"title": "Manual of Accounting Procedure (MAP) Vol II Part IV", "url": "https://epfindia.gov.in/map.pdf"}
            ],
        }

    def _handle_precedents(self, query: str) -> Dict[str, Any]:
        citations, lock_status = self.precedents.search_precedents(query_text=query)
        if citations:
            top = citations[0]
            text = (
                f"### Authoritative Precedent: {top['case_title']}\n\n"
                f"- **Court/Tribunal**: {top['court_or_tribunal']}\n"
                f"- **Case Reference**: `{top['case_number']}` (Dated: {top['order_date']})\n"
                f"- **Key Legal Ratio**: {top['key_holding']}\n\n"
                f"> *\"{top['verbatim_excerpt']}\"*\n\n"
                f"**Citation-Lock Status**: `{lock_status}` (Verified SHA-256: `{top['doc_sha256'][:16]}...`)"
            )
            return {
                "intent": "PRECEDENTS_CASE_LAW",
                "answer_markdown": text,
                "citations": citations,
            }
        return self._handle_general_search(query)

    def _handle_general_search(self, query: str) -> Dict[str, Any]:
        envelope = self.store.get_rule_as_of("statutory_wage_ceiling", {}, date.today())
        text = (
            f"### EPFO Statutory Compliance Intelligence\n\n"
            f"Your query: *\"{query}\"*\n\n"
            f"The EPFO statutory framework is governed by the EPF & MP Act 1952, EPF Scheme 1952, "
            f"EPS 1995, and EDLI Scheme 1976.\n"
            f"- **Statutory Wage Ceiling**: ₹15,000/month (moving to ₹25,000 under 2026 Schemes)\n"
            f"- **Employee Contribution**: 12.00% of statutory wages\n"
            f"- **Employer Split**: 8.33% to EPS Account 10 (capped) + 3.67% to EPF Account 1\n"
            f"- **Late Remittances**: 12% p.a. simple interest under Section 7Q + graded/monthly damages under Section 14B.\n\n"
            f"You can ask specific questions like:\n"
            f"• *'Why was my Form 19 rejected for completed wage month?'*\n"
            f"• *'How does the 50% allowance rule add back to basic wages?'*\n"
            f"• *'Calculate 7Q interest and 14B damages for 45 days on 2 Lakh arrears'*."
        )
        return {
            "intent": "GENERAL_EPFO",
            "answer_markdown": text,
            "citations": [{"title": "EPF & MP Act, 1952", "url": envelope.citation_url, "doc_sha256": envelope.doc_sha256}],
        }
