"""
api/copilot.py
Authoritative Natural Language EPFO Copilot Orchestrator.
Powers the "Ask Anything about EPFO" conversational interface, Telegram Bot,
and Social AI automated briefing engine.
Transforms natural user queries into deterministic Stage 1-5 engine calls,
returning plain-language legal answers locked to statutory citations.
"""

from datetime import date, datetime
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

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

        # 0. Intent: Greetings / Onboarding
        if q_lower in ["hi", "hello", "hey", "namaste", "good morning", "good evening", "good afternoon", "help"]:
            return self._handle_greeting()

        # 1. Intent: Vishwas / Vivad se Vishwas / Dispute Settlement
        if any(w in q_lower for w in ["vishwas", "vishwash", "vivad se vishwas", "dispute settlement", "amnesty"]):
            return self._handle_vishwas_and_disputes(query)

        # 2. Intent: Joint Declaration / Demographic Mismatch
        if any(w in q_lower for w in ["joint declaration", "jd", "father name", "father's name", "name mismatch", "dob correction", "date of birth", "date of joining", "date of exit"]):
            return self._handle_joint_declaration(query)

        # 3. Intent: Advance / Form 31 / Auto-Settlement
        if any(w in q_lower for w in ["advance", "form 31", "auto settlement", "auto-settlement", "auto claim", "illness", "marriage advance", "housing"]):
            return self._handle_advance_and_auto_settlement(query)

        # 4. Intent: Transfer / Form 13 / Annexure K / Service Overlap
        if any(w in q_lower for w in ["transfer", "form 13", "annexure k", "service overlap", "overlap", "previous member", "merge pf"]):
            return self._handle_transfers_and_service_overlap(query)

        # 5. Intent: Section 7A Inquiries / Assessment / Summons
        if any(w in q_lower for w in ["7a", "assessment", "inquiry", "quasi-judicial", "summons", "compliance audit", "inspector"]):
            return self._handle_section_7a_inquiry(query)

        # 6. Intent: Grievances / EPFiGMS / Escalations
        if any(w in q_lower for w in ["grievance", "epfigms", "complaint", "cpgrams", "escalation", "pro", "officer"]):
            return self._handle_grievance_and_epfigms(query)

        # 7. Intent: 7Q Interest & 14B Damages / Penalties / Section 7O Appeal
        if any(w in q_lower for w in ["7q", "14b", "penalty", "penalties", "damages", "delay", "late payment", "7o", "appeal deposit"]):
            return self._handle_penalties(query)

        # 8. Intent: Wage Ceiling
        if any(w in q_lower for w in ["wage ceiling", "statutory ceiling", "salary limit", "wage limit", "ceiling hike", "25000 ceiling", "15000 ceiling"]):
            return self._handle_wage_ceiling(q_lower)

        # 9. Intent: Pension / EPS / EDLI / Withdrawal
        if any(w in q_lower for w in ["pension", "eps", "edli", "form 10c", "withdrawal benefit", "10 years service"]):
            return self._handle_pension_edli(query)

        # 10. Intent: Portal Rejection / Form 19 / Troubleshooting
        if any(w in q_lower for w in ["reject", "rejected", "rejection", "form 19", "dsc", "kyc", "wage month", "speaking order"]):
            return self._handle_claim_troubleshooting(query)

        # 11. Intent: Case Laws / Judgments / Precedents
        if any(w in q_lower for w in ["court", "judgment", "ruling", "supreme court", "high court", "cgit", "tribunal", "case law"]):
            return self._handle_precedents(query)

        # 12. Intent: 50% Allowance Cap Add-Back & Salary Contribution Calculations
        if any(w in q_lower for w in ["calculate", "50%", "allowance cap", "add back", "wage contribution", "pf contribution", "allowances exceed", "basic salary"]):
            return self._handle_50_percent_allowance(query)

        # 13. Fallback: General Semantic & Knowledge Search
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

    def _synthesize_with_gemini(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Uses Google Gemini AI with statutory system grounding to generate
        high-fidelity legal analysis for queries not matching static intent templates.
        """
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("GEMINI_API_KEY="):
                                api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass

        if not api_key:
            return None

        api_key = api_key.replace(" ", "").strip()

        prompt = f"""You are the authoritative Principal Compliance Architect for corporatecompliance.in and the EPFO Intelligence System.
Answer the following statutory compliance question with strict legal accuracy, citing provisions of the EPF & MP Act 1952, EPF Scheme 1952, EPS 1995, EDLI 1976, or Supreme Court / High Court precedents.

User Question: "{query}"

Format your response in clean Markdown with:
### ⚖️ Statutory Legal Position
(Clear statutory analysis with exact paragraph/section numbers)

**Root Cause & Operational Reality:**
(Explanation of portal mechanics, employer responsibilities, or KYC validation)

**Actionable Step-by-Step Resolution:**
1. Step one
2. Step two
3. Step three

**Statutory Citations:**
- Relevant Section / Scheme / Supreme Court ruling.
"""
        model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            txt = parts[0].get("text", "").strip()
                            if txt:
                                return {
                                    "intent": "AI_STATUTORY_SYNTHESIS",
                                    "answer_markdown": txt,
                                    "citations": [
                                        {"title": "EPF & MP Act, 1952 & Allied Schemes", "url": "https://corporatecompliance.in/wiki"},
                                        {"title": "EPFO Standard Operating Procedures", "url": "https://corporatecompliance.in/epfo-error"}
                                    ],
                                }
        except Exception:
            pass
        return None

    def _handle_greeting(self) -> Dict[str, Any]:
        text = (
            "### 🙏 Welcome to the EPFO Statutory Intelligence Assistant\n\n"
            "I provide verified statutory analysis under the **Employees' Provident Funds & Miscellaneous Provisions Act, 1952**.\n\n"
            "**Here are the core areas I can assist you with:**\n"
            "• **Claim Rejections:** Form 19, 10C, 10D troubleshooting, speaking order analysis, and bank KYC fixes.\n"
            "• **Demographic Corrections:** Online Joint Declaration (SOP guidelines for Name, Father's Name, DOB, DOJ, DOE).\n"
            "• **Dispute Settlement:** EPFO *Vivad se Vishwas* guidelines, Section 14B damages waiver, and 7Q interest computation.\n"
            "• **Statutory Calculations:** EPS-95 pension formula, EDLI death benefit, and Supreme Court 50% allowance cap.\n"
            "• **Employer Coverage:** Section 7A inquiry summons, 20+ employee clubbing, and contractor ECR compliance.\n\n"
            "💡 *Ask me anything directly, or send `/ask <your query>`!*"
        )
        return {
            "intent": "GREETING",
            "answer_markdown": text,
            "citations": [
                {"title": "EPF & MP Act, 1952 Official Portal", "url": "https://corporatecompliance.in/wiki"},
                {"title": "EPFO Standard Operating Procedures", "url": "https://corporatecompliance.in/tools"}
            ],
            "actionable_steps": [
                "Type your specific rejection reason or compliance query.",
                "Or upload a photo of your rejection slip for instant statutory OCR triage."
            ]
        }

    def _handle_vishwas_and_disputes(self, query: str) -> Dict[str, Any]:
        text = (
            "### ⚖️ EPFO 'Vishwas' & 'Vivad se Vishwas' Framework\n\n"
            "In EPFO statutory compliance, **'Vishwas'** refers to two major trust-based dispute and claim resolution frameworks:\n\n"
            "1. **EPFO 'Vivad se Vishwas' Statutory Dispute Settlement**:\n"
            "   • **Purpose:** Resolves prolonged litigation and pending statutory inquiries under **Sections 7A, 7Q, and 14B** of the EPF & MP Act, 1952.\n"
            "   • **Damages Relief (Section 14B):** Allows establishments that pay all legitimate employee/employer principal contributions in full to seek substantial relief, reduction, or complete waiver of punitive damages under Section 14B.\n"
            "   • **Interest (Section 7Q):** Simple interest @ 12% per annum is non-waivable by statutory mandate, but compounding interest or prosecution under Section 14 is fully stayed.\n\n"
            "2. **EPFO 'Vishwas' Automated Claim Processing (Auto-Mode)**:\n"
            "   • **Trust-Based Automation:** EPFO introduced an automated algorithmic mechanism (*Project Vishwas*) for processing advance claims under **Form 31** (illness Para 68K, marriage Para 68N, education Para 68B) up to **₹1,00,000**.\n"
            "   • **Zero Human Touch:** Claims are auto-settled within 3 to 4 working days without passing through dealing assistants (DA) or Section Supervisors, provided UAN KYC (Aadhaar & Bank NPCI) is verified and there is no service overlap.\n\n"
            "3. **Contractual Vivad se Vishwas (Government Works)**:\n"
            "   • Contractor establishments facing withheld statutory PF deposits on government infrastructure projects can apply under Vivad se Vishwas II for fast-track dispute settlement."
        )
        return {
            "intent": "VISHWAS_DISPUTE_SETTLEMENT",
            "answer_markdown": text,
            "citations": [
                {"title": "EPF & MP Act, 1952 — Sections 7A, 7Q & 14B", "url": "https://corporatecompliance.in/wiki"},
                {"title": "EPFO Standard Operating Procedure on Auto-Settlement (Form 31)", "url": "https://corporatecompliance.in/tools"},
                {"title": "Ministry of Labour Guidelines on Dispute Resolution", "url": "https://corporatecompliance.in/wiki"}
            ],
            "actionable_steps": [
                "For Claims: Ensure UAN has validated Bank KYC and active mobile number to trigger auto-settlement mode.",
                "For Damages Defense: Submit an application for settlement under Section 14B guidelines along with proof of principal dues payment.",
                "Book an advocate consultation at corporatecompliance.in/cases/create for tailored 7A/14B representation."
            ]
        }

    def _handle_joint_declaration(self, query: str) -> Dict[str, Any]:
        text = (
            "### ⚖️ EPFO Joint Declaration Standard Operating Procedure (SOP)\n\n"
            "Under the comprehensive **Joint Declaration SOP (Circular No. WSU/2022/1/UIDAI/3009)**, correction of member demographic details is governed by strict statutory tiers:\n\n"
            "1. **Minor Corrections (Up to 2 Characters / 3 Years DOB)**:\n"
            "   • Can be initiated online directly through the Member e-Sewa portal.\n"
            "   • Requires employer digital attestation (DSC) and supporting documents (Aadhaar / Passport / PAN / School Certificate).\n"
            "   • Processing SLA: **7 to 15 days**.\n\n"
            "2. **Major Corrections (Full Name Change / >3 Years DOB / Father Name Mismatch)**:\n"
            "   • Requires 3 supporting statutory documents (e.g. Gazette notification for name change, 10th marksheet for DOB, Father's Aadhaar/Voter ID).\n"
            "   • Approval Level: Cleared by Regional PF Commissioner (RPFC-I / RPFC-II).\n\n"
            "3. **Closed Establishment Exception**:\n"
            "   • If your previous establishment has closed down or become untraceable, you can submit a physical Joint Declaration attested by a **Bank Manager**, Gazetted Officer, or Magistrate directly to the field office PRO without employer DSC."
        )
        return {
            "intent": "JOINT_DECLARATION_SOP",
            "answer_markdown": text,
            "citations": [
                {"title": "EPFO Joint Declaration SOP (WSU/2022/1/UIDAI/3009)", "url": "https://corporatecompliance.in/wiki"},
                {"title": "EPF Scheme 1952 — Paragraph 26B & 28", "url": "https://corporatecompliance.in/wiki"}
            ],
            "actionable_steps": [
                "Login to Member e-Sewa -> Manage -> Joint Declaration.",
                "Select Member ID and enter exact details matching Aadhaar card.",
                "Upload color PDF of supporting identity proof.",
                "Request employer to approve the JD in Employer Unified Portal -> Member -> Joint Declaration."
            ]
        }

    def _handle_advance_and_auto_settlement(self, query: str) -> Dict[str, Any]:
        text = (
            "### ⚖️ EPFO Form 31 Advance & Auto-Settlement Protocol\n\n"
            "EPF members can withdraw non-refundable advances under **Form 31** without exiting service:\n\n"
            "1. **Auto-Settlement Mode (Limit: ₹1,00,000)**:\n"
            "   • Claims under **Para 68K (Illness/Hospitalization)**, **Para 68B (Housing)**, and **Para 68N (Marriage/Education)** are auto-processed within 3–4 days by the IT system.\n"
            "   • No document upload (no medical certificate/wedding card) is required for illness advances.\n\n"
            "2. **Advance Parameters by Purpose**:\n"
            "   • **Illness (Self/Family - Para 68K):** Up to 6 months' basic wages or employee share with interest (no minimum service).\n"
            "   • **Marriage (Self/Children/Siblings - Para 68N):** Up to 50% of employee share with interest (requires 7 years of service, maximum 3 times).\n"
            "   • **Housing/Plot (Para 68B):** Up to 24 to 36 months' basic wages or total balance (requires 5 years of service).\n\n"
            "3. **Common Reasons for Auto-Claim Failure**:\n"
            "   • Mismatch in bank account name vs UAN profile.\n"
            "   • Unlinked/unverified Aadhaar or unseeded bank IFSC."
        )
        return {
            "intent": "FORM_31_ADVANCE",
            "answer_markdown": text,
            "citations": [
                {"title": "EPF Scheme 1952 — Paragraphs 68B, 68K, 68N", "url": "https://corporatecompliance.in/wiki"},
                {"title": "EPFO Auto-Settlement Circular 2024", "url": "https://corporatecompliance.in/tools"}
            ],
            "actionable_steps": [
                "Log in to Member e-Sewa -> Online Services -> Claim (Form 31, 19, 10C, 10D).",
                "Verify last 4 digits of bank account.",
                "Select Form 31 and choose Purpose of Advance: 'Illness' for fastest auto-settlement."
            ]
        }

    def _handle_transfers_and_service_overlap(self, query: str) -> Dict[str, Any]:
        text = (
            "### ⚖️ EPF Member Transfer (Form 13) & Service Overlap Protocol\n\n"
            "Transferring PF accumulations between establishments is governed by Paragraph 57 of the EPF Scheme, 1952:\n\n"
            "1. **Online Transfer (Form 13 via Member e-Sewa)**:\n"
            "   • Navigate to Online Services -> One Member - One EPF Account (Transfer Request).\n"
            "   • Attestation can be chosen through either **Previous Employer** or **Present Employer**.\n\n"
            "2. **Service Overlap Issues**:\n"
            "   • Occurs when Date of Joining in new company is earlier than Date of Exit in previous company.\n"
            "   • **Statutory Remedy:** Date of Exit must be rectified by previous employer via employer portal or Joint Declaration. Dual contribution for the same period is legally prohibited.\n\n"
            "3. **Annexure K Generation**:\n"
            "   • Once transfer is approved by field office, Annexure K is digitally generated, carrying the EPS service breakdown and transferred wage months."
        )
        return {
            "intent": "TRANSFER_AND_OVERLAP",
            "answer_markdown": text,
            "citations": [
                {"title": "EPF Scheme, 1952 — Paragraph 57", "url": "https://corporatecompliance.in/wiki"},
                {"title": "EPFO Circular on Auto-Transfer of PF Balances", "url": "https://corporatecompliance.in/tools"}
            ],
            "actionable_steps": [
                "Check Date of Exit in previous service before applying for transfer.",
                "Select 'Present Employer' for faster digital DSC attestation.",
                "Track transfer status in View -> Track Claim Status."
            ]
        }

    def _handle_section_7a_inquiry(self, query: str) -> Dict[str, Any]:
        text = (
            "### ⚖️ Section 7A Quasi-Judicial Inquiries & Assessment\n\n"
            "Under **Section 7A of the EPF & MP Act, 1952**, the Central/Regional PF Commissioner acts as a Quasi-Judicial Authority with powers of a Civil Court (CPC 1908):\n\n"
            "1. **Scope of Inquiry**:\n"
            "   • Determination of establishment coverage (clubbing of units/branches).\n"
            "   • Assessment of statutory dues payable in respect of regular, contract, or casual employees.\n\n"
            "2. **Statutory Safeguards for Employers**:\n"
            "   • **No Ex-Parte Orders without Notice:** The authority cannot assess dues without issuing Form 7A notice and affording an opportunity of personal hearing.\n"
            "   • **Speaking Order Mandate:** The assessing officer must pass a reasoned speaking order establishing employer-employee relationship and wage bifurcation.\n\n"
            "3. **Remedies Against 7A Order**:\n"
            "   • **Review under Section 7B:** Application for review can be filed within 45 days upon discovery of new evidence.\n"
            "   • **Appeal under Section 7-I to CGIT:** Appeal lies before the Central Government Industrial Tribunal within 60 days, subject to Section 7O pre-deposit (75% or waiver)."
        )
        return {
            "intent": "SECTION_7A_INQUIRY",
            "answer_markdown": text,
            "citations": [
                {"title": "EPF & MP Act, 1952 — Section 7A, 7B, 7-I, 7O", "url": "https://corporatecompliance.in/wiki"},
                {"title": "Supreme Court Precedent — Food Corporation of India vs. Provident Fund Commissioner", "url": "https://corporatecompliance.in/wiki"}
            ],
            "actionable_steps": [
                "Never ignore a 7A summons; file a written statement of defense on or before the hearing date.",
                "Maintain complete muster rolls, wage registers, and contractor ECR challans.",
                "Engage qualified legal representation on corporatecompliance.in/cases/create."
            ]
        }

    def _handle_grievance_and_epfigms(self, query: str) -> Dict[str, Any]:
        text = (
            "### ⚖️ EPFO EPFiGMS Grievance & Escalation Protocol\n\n"
            "If your claim is arbitrarily rejected, delayed beyond 20 days, or KYC is unapproved:\n\n"
            "1. **EPFiGMS Registration (epfigms.gov.in)**:\n"
            "   • Lodge formal grievance selecting category: *PF Member*, *EPS Pensioner*, or *Employer*.\n"
            "   • Enter UAN, Claim ID, and exact rejection remarks.\n"
            "   • Statutory SLA: Must be resolved or replied within **20 working days**.\n\n"
            "2. **Sub-Regional / Regional Level Escalation**:\n"
            "   • If field office gives vague boilerplate reply, submit a reminder / feedback flag on EPFiGMS.\n"
            "   • Escalate to CPGRAMS (pgportal.gov.in) under Ministry of Labour & Employment for oversight.\n\n"
            "3. **Public Relations Officer (PRO) Intervention**:\n"
            "   • Every EPFO Regional Office operates a Bhavishya Nidhi Adalat on the 10th of every month for physical dispute resolution."
        )
        return {
            "intent": "EPFIGMS_GRIEVANCE",
            "answer_markdown": text,
            "citations": [
                {"title": "EPFO Citizen's Charter", "url": "https://corporatecompliance.in/wiki"},
                {"title": "CPGRAMS Department of Administrative Reforms Guidelines", "url": "https://corporatecompliance.in/tools"}
            ],
            "actionable_steps": [
                "Visit epfigms.gov.in -> Register Grievance.",
                "Attach PDF copy of your rejection slip or grievance order.",
                "Note registration number for statutory escalation."
            ]
        }

    def _handle_general_search(self, query: str) -> Dict[str, Any]:
        # 1. Try Gemini Generative AI synthesis if configured
        ai_res = self._synthesize_with_gemini(query)
        if ai_res:
            return ai_res

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
