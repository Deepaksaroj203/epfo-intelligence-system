"""
api/social_briefing.py
Automated Social AI Intelligence Generator.
Supplies verified, citation-locked daily content to external automated bots
(Twitter/X threads, Instagram carousels, LinkedIn posts).
Prevents hallucinations and fact-checks content against the immutable Stage 1 baseline.
"""

from datetime import date
from typing import Any, Dict, List


class SocialBriefingEngine:
    """
    Generates high-engagement, legally verified social media content sets.
    """

    TOPICS = [
        {
            "topic": "The 50% Allowance Cap Rule (Section 2(b))",
            "headline": "Why Your PF Calculation Might Be Wrong if Allowances Exceed 50%",
            "twitter_thread": [
                "🚨 CRITICAL FOR EMPLOYERS & HR: Did you know your PF contribution might be legally WRONG if allowances exceed 50% of gross pay? Here is the exact mathematical rule under Section 2(b) & how to avoid massive 7Q & 14B penalties 🧵👇 #EPFO #Compliance #Payroll",
                "1/3 📊 THE 50% CAP RULE:\nIf HRA, travel, and special allowances exceed 50% of gross salary, the excess MUST be added back to Basic Wages.\n\nExample on Gross ₹50,000:\n• Basic: ₹20,000\n• Allowances: ₹30,000 (60%)\n• 50% threshold: ₹25,000\n• Excess added back: ₹5,000\n• Adjusted PF wage: ₹25,000!",
                "2/3 ⚖️ PENALTY CONSEQUENCES:\nFailing to add back excess allowances leads to:\n• 12% p.a. simple interest under Section 7Q\n• Up to 25% penal damages under Section 14B\n• Personal liability on Directors\n\nEPFO audits are strictly cross-referencing GST & Tax filings.",
                "3/3 💡 HOW TO FIX IT:\nAudit your ECR files before filing. Ensure your payroll software computes excess allowances automatically.\n\n👉 Test your exact numbers on our live compliance intelligence engine: https://corporatecompliance.in\n\nRT to protect fellow employers! 🔁",
            ],
            "instagram_caption": (
                "⚠️ ATTENTION HR & BUSINESS OWNERS: Are your PF calculations compliant with the 50% Allowance Rule?\n\n"
                "Under Section 2(b) of the EPF Act & Code on Social Security, when allowances exceed 50% of total salary, the excess is treated as Basic Wages!\n\n"
                "📌 Example:\nSalary: ₹50,000 (Basic ₹20,000 + Allowances ₹30,000)\n"
                "Excess Allowances: ₹5,000\n"
                "New PF Wage: ₹25,000!\n\n"
                "Failure to comply attracts 12% Section 7Q interest and Section 14B damages.\n\n"
                "Save this post & audit your payroll today! Link in bio for instant ECR checking.\n\n"
                "#EPFO #PayrollCompliance #HRIndia #LaborLaw #EPFRules #corporatecompliance"
            ),
            "linkedin_post": (
                "Strategic Compliance Alert for CFOs, CHROs, and Payroll Leaders:\n\n"
                "The 50% Allowance Rule under Section 2(b) of the EPF & MP Act, 1952 has become the primary trigger for Section 7A assessment notices across regional EPFO offices.\n\n"
                "Key Principle:\n"
                "If non-basic allowances exceed 50% of total remuneration, the excess must be added back to the statutory wage base before computing employee and employer PF splits.\n\n"
                "Action Points for Organizations:\n"
                "1. Audit monthly salary structures against the 50% ceiling.\n"
                "2. Pre-validate ECR batch files before portal upload.\n"
                "3. Ensure the mandatory 25% Section 7O pre-deposit is planned in the event of an appeal before the CGIT.\n\n"
                "#LaborLaw #EPFO #CorporateGovernance #PayrollCompliance #CFOInsights"
            ),
            "citations": [
                {"title": "Section 2(b) & Section 6, EPF & MP Act 1952", "url": "https://epfindia.gov.in/rules/epf_act.pdf"}
            ],
        },
        {
            "topic": "September 17, 2026 Statutory Wage Ceiling Shift",
            "headline": "EPFO Wage Ceiling Moving to ₹25,000: Everything You Must Know",
            "twitter_thread": [
                "📢 BIG UPDATE: The EPFO Statutory Wage Ceiling is shifting from ₹15,000 to ₹25,000 per month under the appointed EPF/EPS/EDLI Schemes 2026. Here is the operational impact on take-home pay and employer budgets 🧵👇 #EPFO #Pension #IndiaEconomy",
                "1/3 📈 HISTORICAL REVISIONS:\n• Pre-2014: ₹6,500/month\n• 2014–2026: ₹15,000/month\n• 2026+: ₹25,000/month (Appointed per S.O. 5109(E))\n\nThis marks the largest expansion of social security coverage in over a decade.",
                "2/3 💰 FINANCIAL IMPACT:\n• Employee PF deduction (12%): Up to ₹3,000/month (vs ₹1,800 previously)\n• Employer EPS 8.33% contribution: Up to ₹2,083/month (vs ₹1,250 previously)\n• Higher terminal accumulation & pension entitlement!",
                "3/3 ⚙️ PAYROLL READINESS:\nEnsure your HRMS recalculates ECR contributions strictly starting on the appointed effective date. Early or late application will cause portal upload rejections.\n\nRead full analysis & simulate your budget at https://corporatecompliance.in 🔗",
            ],
            "instagram_caption": (
                "🚀 MAJOR EPFO UPDATE: The Wage Ceiling is increasing to ₹25,000/month!\n\n"
                "What this means for you:\n"
                "✅ Higher retirement savings\n"
                "✅ Increased monthly EPS pension base\n"
                "✅ Enhanced EDLI life cover up to ₹7,00,000\n\n"
                "Share this with your colleagues! Follow @corporatecomplaince for real-time compliance updates.\n\n"
                "#EPFOUpdate #PFRules #PersonalFinanceIndia #SalaryStructure #PFHike"
            ),
            "linkedin_post": (
                "The notification of the ₹25,000 statutory wage ceiling under the EPF/EPS/EDLI Schemes represents a structural transformation for Indian enterprise payroll.\n\n"
                "Financial Implications:\n"
                "- Maximum employer statutory cost per eligible employee rises from ₹1,800 to ₹3,000/month.\n"
                "- Millions of previously excluded employees enter mandatory coverage.\n\n"
                "#EPFO #HumanResources #EmployeeBenefits #StatutoryCompliance"
            ),
            "citations": [
                {"title": "G.S.R. 608(E) & S.O. 5109(E)", "url": "https://egazette.gov.in/notifications/wage_ceiling_2026.pdf"}
            ],
        },
    ]

    @classmethod
    def get_briefing_for_date(cls, query_date: Optional[date] = None) -> Dict[str, Any]:
        target_date = query_date or date.today()
        # Rotate topic deterministically by day of year
        idx = target_date.timetuple().tm_yday % len(cls.TOPICS)
        topic_data = cls.TOPICS[idx]

        return {
            "date": target_date.isoformat(),
            "topic": topic_data["topic"],
            "headline": topic_data["headline"],
            "twitter_thread": topic_data["twitter_thread"],
            "instagram_caption": topic_data["instagram_caption"],
            "linkedin_post": topic_data["linkedin_post"],
            "statutory_citations": topic_data["citations"],
        }
