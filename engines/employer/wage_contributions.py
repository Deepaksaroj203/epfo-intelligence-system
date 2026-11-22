"""
engines/employer/wage_contributions.py
Employer-side deterministic wage definition, 50% excluded allowance add-back,
statutory wage ceiling resolution, and EPF/EPS/EDLI contribution splits engine.
Implements:
- 50% excluded-pay add-back test (Supreme Court Vivekananda Vidyamandir & Code on Social Security)
- Point-in-time statutory wage ceiling lookup via get_rule_as_of()
- Integer paise arithmetic with statutory ECR rounding policies
"""

from datetime import date
from typing import Dict, List, Optional
from db.statutory_store import StatutoryStore
from engines.common import EngineResult, EmployerCaseInput


def evaluate_wage_contributions(case: EmployerCaseInput, store: StatutoryStore) -> EngineResult:
    """
    Computes statutory wages, applies the 50% excluded pay add-back rule,
    resolves the effective wage ceiling, and calculates all EPF/EPS/EDLI splits in integer paise.
    """
    eval_date = case.wage_month or case.evaluation_date
    working_steps: List[str] = []
    blockers: List[str] = []

    # 1. Retrieve statutory wage ceiling from Stage 1 as of the wage month
    ceiling_env = store.get_rule_as_of("statutory_wage_ceiling", event_date=eval_date)
    wage_ceiling_paise = ceiling_env.value_numeric or 1500000

    working_steps.append(
        f"Statutory Wage Ceiling as of {eval_date.strftime('%d-%b-%Y')}: "
        f"₹{wage_ceiling_paise / 100:,.2f} ({ceiling_env.verbatim_quote.strip()})."
    )

    # 2. 50% Excluded Allowance Add-Back Test (SC Vivekananda Vidyamandir 2019 & Code 2020)
    gross_paise = case.gross_wages_paise
    basic_paise = case.basic_wages_paise
    excluded_paise = case.excluded_allowances_paise

    fifty_percent_threshold = int(gross_paise * 0.50)
    excess_allowances_paise = max(0, excluded_paise - fifty_percent_threshold)

    adjusted_statutory_wage_paise = basic_paise + excess_allowances_paise

    if excess_allowances_paise > 0:
        working_steps.append(
            f"50% Excluded Pay Add-Back Triggered: Total Gross ₹{gross_paise / 100:,.2f}. "
            f"Excluded allowances ₹{excluded_paise / 100:,.2f} exceed 50% cap (₹{fifty_percent_threshold / 100:,.2f}) "
            f"by ₹{excess_allowances_paise / 100:,.2f}. "
            f"Excess ₹{excess_allowances_paise / 100:,.2f} added back to basic wages (₹{basic_paise / 100:,.2f}) -> "
            f"Adjusted Statutory EPF Wage: ₹{adjusted_statutory_wage_paise / 100:,.2f}."
        )
    else:
        working_steps.append(
            f"50% Excluded Pay Rule Satisfied: Excluded allowances ₹{excluded_paise / 100:,.2f} <= 50% gross. "
            f"Statutory EPF Wage: ₹{adjusted_statutory_wage_paise / 100:,.2f}."
        )

    # 3. Determine Capped Wage for EPS and EDLI
    # EPS and EDLI are capped at the statutory ceiling (unless higher pension validly opted)
    capped_wage_paise = min(adjusted_statutory_wage_paise, wage_ceiling_paise)
    working_steps.append(
        f"Ceiling Capping: Adjusted wage ₹{adjusted_statutory_wage_paise / 100:,.2f} vs Ceiling ₹{wage_ceiling_paise / 100:,.2f} -> "
        f"Capped Wage for EPS/EDLI: ₹{capped_wage_paise / 100:,.2f}."
    )

    # 4. Check Age-58 EPS Block (Re-Engineered ECR v3.0 Rule)
    is_eps_eligible = True
    if case.member_age >= 58 and not case.is_deferred_pension:
        is_eps_eligible = False
        working_steps.append(
            f"Age-58 EPS Block: Member age {case.member_age} >= 58 without deferred pension flag. "
            f"EPS contribution set to ₹0. Full 12% employer contribution diverted to EPF Account 1."
        )

    # Check post-Sept 2014 New Joinee Excluded Employee Rule
    if case.member_joining_date and case.member_joining_date >= date(2014, 9, 1):
        if adjusted_statutory_wage_paise > wage_ceiling_paise and not case.opted_higher_pension:
            is_eps_eligible = False
            working_steps.append(
                f"Post-Sept 2014 Excluded Employee: Member joined after 01-Sep-2014 with wage "
                f"₹{adjusted_statutory_wage_paise / 100:,.2f} exceeding ceiling. Excluded from EPS."
            )

    # 5. Compute Statutory Contribution Splits in Integer Paise
    # Rates: EE 12%, ER EPS 8.33%, ER EPF net 3.67%, EDLI 0.50%, Admin 0.50%
    # Employee EPF Share (12.00% on statutory wage or ceiling)
    # If unexempted and contributions capped at ceiling:
    ee_epf_base_paise = capped_wage_paise
    ee_epf_paise = store.apply_rounding("ECR", int(ee_epf_base_paise * 0.12))

    # Employer EPS Share (8.33% on capped wage)
    if is_eps_eligible:
        er_eps_paise = store.apply_rounding("ECR", int(capped_wage_paise * 0.0833))
    else:
        er_eps_paise = 0

    # Employer EPF Share (Account 1: 12% total employer contribution minus EPS contribution)
    total_er_statutory_paise = store.apply_rounding("ECR", int(ee_epf_base_paise * 0.12))
    er_epf_paise = max(0, total_er_statutory_paise - er_eps_paise)

    # EDLI Share (Account 21: 0.50% on capped wage)
    edli_paise = store.apply_rounding("ECR", int(capped_wage_paise * 0.005))

    # EPF Administrative Charges (Account 2: 0.50% on statutory wages, minimum ₹500/₹75)
    raw_admin_paise = int(ee_epf_base_paise * 0.005)
    admin_charges_paise = store.apply_rounding("ADMIN_CHARGES", raw_admin_paise)

    # Total statutory monthly challan obligation
    total_challan_paise = ee_epf_paise + er_epf_paise + er_eps_paise + edli_paise + admin_charges_paise

    working_steps.append(
        f"Calculated Contribution Splits (Integer Paise): "
        f"EE EPF: ₹{ee_epf_paise / 100:,.2f} (12%), "
        f"ER EPS: ₹{er_eps_paise / 100:,.2f} (8.33%), "
        f"ER EPF: ₹{er_epf_paise / 100:,.2f} (3.67%), "
        f"EDLI: ₹{edli_paise / 100:,.2f} (0.50%), "
        f"Admin: ₹{admin_charges_paise / 100:,.2f}. "
        f"Total Monthly Obligation: ₹{total_challan_paise / 100:,.2f}."
    )

    return EngineResult(
        value={
            "gross_wages_paise": gross_paise,
            "basic_wages_paise": basic_paise,
            "excluded_allowances_paise": excluded_paise,
            "excess_allowances_added_back_paise": excess_allowances_paise,
            "adjusted_statutory_wage_paise": adjusted_statutory_wage_paise,
            "capped_wage_paise": capped_wage_paise,
            "statutory_wage_ceiling_paise": wage_ceiling_paise,
            "ee_epf_paise": ee_epf_paise,
            "er_eps_paise": er_eps_paise,
            "er_epf_paise": er_epf_paise,
            "edli_paise": edli_paise,
            "admin_charges_paise": admin_charges_paise,
            "total_challan_paise": total_challan_paise,
            "is_eps_eligible": is_eps_eligible,
        },
        working_steps=working_steps,
        blockers=blockers,
        approval_tier="CONTRIBUTION_CALCULATION",
        judicial_notes=ceiling_env.judicial_notes or "Supreme Court Vivekananda Vidyamandir (2019) 50% wage rule applied.",
        troubleshooting_tips=[],
        rule_id=ceiling_env.rule_id,
        citation_url=ceiling_env.citation_url,
        doc_sha256=ceiling_env.doc_sha256,
        evaluated_as_of_date=str(eval_date),
        metadata={
            "wage_month": str(case.wage_month),
            "member_age": case.member_age,
        },
    )
