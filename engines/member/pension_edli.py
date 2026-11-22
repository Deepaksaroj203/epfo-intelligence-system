"""
engines/member/pension_edli.py
Member-side deterministic pension (EPS-95) and insurance (EDLI) entitlement engine.
Implements:
- 10-year pensionable service gate (withdrawal vs monthly pension)
- Employer default period exclusion from EPS withdrawal benefit calculation
- Early reduced pension (age 50–57, 4% per year discount) vs Superannuation (age 58)
- EDLI death-in-service assurance benefit calculation (min ₹2.5L, max ₹7.0L)
"""

from datetime import date
from typing import Dict, List, Optional
from db.statutory_store import StatutoryStore
from engines.common import EngineResult, MemberCaseInput


def evaluate_pension_and_edli(
    case: MemberCaseInput,
    store: StatutoryStore,
    is_death_in_service: bool = False,
    average_pf_balance_paise: int = 0
) -> EngineResult:
    """
    Computes pensionable service, withdrawal benefit with employer-default exclusion,
    and EDLI insurance assurance benefits.
    """
    eval_date = case.evaluation_date
    working_steps: List[str] = []
    blockers: List[str] = []
    troubleshooting_tips: List[Dict[str, Any]] = []

    # 1. Query current statutory wage ceiling from Stage 1
    ceiling_env = store.get_rule_as_of("statutory_wage_ceiling", event_date=eval_date)
    statutory_ceiling_paise = ceiling_env.value_numeric or 1500000

    # 2. Compute gross service duration in months
    end_date = case.exit_date or eval_date
    gross_months = (end_date.year - case.joining_date.year) * 12 + (end_date.month - case.joining_date.month)
    if case.joining_date.day > 4 and gross_months > 0:
        gross_months -= 1

    ncp_months = case.non_contributory_service_days // 30
    total_eligible_months = max(0, gross_months - ncp_months)

    # 3. Deduct Employer Default Months from EPS Service Credit (MEM-02 Rule)
    defaulted_months = case.employer_default_months
    net_pensionable_months = max(0, total_eligible_months - defaulted_months)

    if defaulted_months > 0:
        working_steps.append(
            f"Employer Default Period Detected: {defaulted_months} months of unremitted EPS contributions. "
            f"Per EPFO Operational Guidelines & EPS-95 Para 10, defaulted {defaulted_months} months are EXCLUDED "
            f"from pensionable service credit (Gross: {total_eligible_months}m -> Net: {net_pensionable_months}m) "
            f"until recovered by EPFO Enforcement Wing under Section 7A."
        )
        troubleshooting_tips.append({
            "code": "EPS_DEFAULT_PERIOD_EXCLUDED",
            "message": f"Employer failed to remit {defaulted_months} months. File grievance on EPFiGMS for Section 7A recovery.",
            "link": "https://epfigms.gov.in"
        })
    else:
        working_steps.append(f"Zero employer defaults. Full contributory tenure of {net_pensionable_months} months credited.")

    net_pensionable_years = net_pensionable_months / 12.0

    # 4. Determine Pension vs Withdrawal Benefit
    is_pension_eligible = net_pensionable_months >= 120  # 10 years = 120 months
    pension_type = "NONE"
    monthly_pension_paise = 0
    withdrawal_benefit_paise = 0

    if is_pension_eligible:
        working_steps.append(
            f"Net service {net_pensionable_months} months >= 10 years (120 months): "
            f"Eligible for Monthly Pension under EPS-95. Form 10C Withdrawal Benefit is BLOCKED."
        )
        # Pensionable salary capped at statutory wage ceiling
        pensionable_salary_paise = min(case.wage_paise, statutory_ceiling_paise)
        # Standard EPS formula: (Pensionable Salary x Pensionable Service) / 70
        base_pension_paise = store.apply_rounding(
            "EPS", int((pensionable_salary_paise * net_pensionable_years) / 70)
        )

        member_age = case.age
        if member_age >= 58:
            pension_type = "SUPERANNUATION_PENSION"
            monthly_pension_paise = base_pension_paise
            working_steps.append(f"Member age {member_age} >= 58: Full superannuation pension awarded: ₹{monthly_pension_paise / 100:,.2f}/month.")
        elif 50 <= member_age < 58:
            pension_type = "EARLY_REDUCED_PENSION"
            # Discounted by 4% for every year short of 58
            years_short = 58 - member_age
            reduction_factor = max(0.0, 1.0 - (0.04 * years_short))
            monthly_pension_paise = store.apply_rounding("EPS", int(base_pension_paise * reduction_factor))
            working_steps.append(
                f"Member age {member_age} (between 50 and 57): Early reduced pension awarded "
                f"({years_short} years short of 58, 4% p.a. discount -> factor {reduction_factor:.2f}): "
                f"₹{monthly_pension_paise / 100:,.2f}/month."
            )
        else:
            pension_type = "SCHEME_CERTIFICATE_MANDATORY"
            monthly_pension_paise = 0
            working_steps.append(f"Member age {member_age} < 50: Must obtain Scheme Certificate; pension payable upon attaining age 50/58.")
    else:
        pension_type = "WITHDRAWAL_BENEFIT"
        working_steps.append(
            f"Net service {net_pensionable_months} months < 10 years: "
            f"Eligible for Form 10C Lump-Sum Withdrawal Benefit."
        )
        # EPS Table D Withdrawal Benefit Factor based on net contributory years
        capped_wage = min(case.wage_paise, statutory_ceiling_paise)
        # Simplified Table D factor: ~1.02 per year of service
        withdrawal_benefit_paise = store.apply_rounding(
            "EPS", int(capped_wage * max(0.5, net_pensionable_years * 1.02))
        )
        working_steps.append(f"Calculated Form 10C Withdrawal Benefit: ₹{withdrawal_benefit_paise / 100:,.2f}.")

    # 5. EDLI Death-in-Service Benefit Evaluation
    edli_benefit_paise = 0
    if is_death_in_service:
        if total_eligible_months >= 12:
            capped_wage = min(case.wage_paise, statutory_ceiling_paise)
            # Formula: 35 x average monthly wage + 50% of avg balance up to ₹1.75L
            base_edli = 35 * capped_wage
            balance_bonus = min(int(average_pf_balance_paise * 0.50), 17500000)
            raw_edli = base_edli + balance_bonus

            # Statutory floors and caps: min ₹2,50,000 (25000000 paise), max ₹7,00,000 (70000000 paise)
            edli_benefit_paise = max(25000000, min(raw_edli, 70000000))
            working_steps.append(
                f"EDLI Death-in-Service Benefit: Continuous service {total_eligible_months}m >= 12m. "
                f"Calculated raw: ₹{raw_edli / 100:,.2f} -> Enforcing statutory range [₹2.5L, ₹7.0L]: "
                f"Final EDLI Assurance Benefit: ₹{edli_benefit_paise / 100:,.2f}."
            )
        else:
            blockers.append(
                f"EDLI_INELIGIBLE: Service tenure {total_eligible_months} months is under 12 months requirement."
            )

    return EngineResult(
        value={
            "pension_type": pension_type,
            "net_pensionable_months": net_pensionable_months,
            "defaulted_months_excluded": defaulted_months,
            "monthly_pension_paise": monthly_pension_paise,
            "withdrawal_benefit_paise": withdrawal_benefit_paise,
            "edli_benefit_paise": edli_benefit_paise,
            "statutory_wage_ceiling_paise": statutory_ceiling_paise,
        },
        working_steps=working_steps,
        blockers=blockers,
        approval_tier="TIER_1_STANDARD",
        judicial_notes=None,
        troubleshooting_tips=troubleshooting_tips,
        rule_id="RULE_EPS_95_AND_EDLI_1976",
        citation_url="https://www.epfindia.gov.in/site_en/Rules_Regulations.php",
        doc_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        evaluated_as_of_date=str(eval_date),
        metadata={
            "gross_service_months": total_eligible_months,
            "defaulted_months": defaulted_months,
            "is_death_in_service": is_death_in_service,
        },
    )
