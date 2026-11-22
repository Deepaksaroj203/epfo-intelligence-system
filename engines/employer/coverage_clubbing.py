"""
engines/employer/coverage_clubbing.py
Employer-side deterministic establishment coverage and Section 2A branch clubbing engine.
Implements:
- 20+ employee statutory coverage threshold
- Section 2A branch / department / factory clubbing rules
- Section 1(5) continuous coverage mandate (permanent coverage once reached 20)
- Section 1(4) voluntary coverage rules
"""

from datetime import date
from typing import Dict, List, Optional
from db.statutory_store import StatutoryStore
from engines.common import EngineResult, EmployerCaseInput


def evaluate_establishment_coverage(
    case: EmployerCaseInput,
    store: StatutoryStore,
    was_previously_covered: bool = False,
    is_voluntary_application: bool = False,
) -> EngineResult:
    """
    Evaluates whether an establishment is statutorily covered under EPF & MP Act 1952
    and Code on Social Security 2020.
    """
    eval_date = case.evaluation_date
    working_steps: List[str] = []
    blockers: List[str] = []
    troubleshooting_tips: List[Dict[str, Any]] = []

    # 1. Retrieve statutory coverage threshold (20 employees)
    threshold_env = store.get_rule_as_of("statutory_coverage_headcount", event_date=eval_date)
    threshold_headcount = threshold_env.value_numeric or 20

    is_covered = False
    coverage_basis = "NOT_COVERED"

    # 2. Section 1(5) Continuous Coverage Rule
    # Once an establishment is covered, it continues to be governed by the Act even if headcount drops below 20.
    if was_previously_covered:
        is_covered = True
        coverage_basis = "SECTION_1_5_CONTINUOUS_COVERAGE"
        working_steps.append(
            f"Section 1(5) Mandate: Establishment was previously covered under the Act. "
            f"Coverage is irrevocable and continues unconditionally even though current headcount is {case.employee_count} (< {threshold_headcount})."
        )

    # 3. Section 2A Branch & Department Clubbing Rule
    elif case.branch_count > 1:
        working_steps.append(
            f"Section 2A Clubbing Analysis: Establishment operates {case.branch_count} branches/departments. "
            f"Total unified headcount: {case.employee_count} employees."
        )
        if case.employee_count >= threshold_headcount:
            is_covered = True
            coverage_basis = "SECTION_2A_BRANCH_CLUBBED_COVERAGE"
            working_steps.append(
                f"Statutory Threshold Met via Section 2A: Aggregate headcount {case.employee_count} >= {threshold_headcount}. "
                f"All {case.branch_count} branches are clubbed as one establishment and covered simultaneously."
            )
        else:
            working_steps.append(
                f"Clubbed headcount {case.employee_count} < statutory threshold {threshold_headcount}. Not mandatorily covered."
            )

    # 4. Standard Single-Unit Mandatory Coverage
    elif case.employee_count >= threshold_headcount:
        is_covered = True
        coverage_basis = "SECTION_1_3_MANDATORY_COVERAGE"
        working_steps.append(
            f"Section 1(3) Threshold Satisfied: Employee headcount {case.employee_count} >= {threshold_headcount}."
        )

    # 5. Section 1(4) Voluntary Coverage
    elif is_voluntary_application:
        is_covered = True
        coverage_basis = "SECTION_1_4_VOLUNTARY_GAZETTE_COVERAGE"
        working_steps.append(
            "Section 1(4) Voluntary Coverage: Applied jointly by employer and majority employees, published in Gazette."
        )
    else:
        working_steps.append(
            f"Headcount {case.employee_count} is under statutory threshold {threshold_headcount}. No mandatory coverage."
        )

    return EngineResult(
        value={
            "is_covered": is_covered,
            "coverage_basis": coverage_basis,
            "total_headcount": case.employee_count,
            "branch_count": case.branch_count,
            "statutory_threshold": threshold_headcount,
        },
        working_steps=working_steps,
        blockers=blockers,
        approval_tier="COVERAGE_DETERMINATION",
        judicial_notes="Section 2A clubbing confirmed by Supreme Court in Transport Corp of India & Regional Provident Fund Commissioner.",
        troubleshooting_tips=troubleshooting_tips,
        rule_id=threshold_env.rule_id,
        citation_url=threshold_env.citation_url,
        doc_sha256=threshold_env.doc_sha256,
        evaluated_as_of_date=str(eval_date),
        metadata={
            "was_previously_covered": was_previously_covered,
            "is_voluntary": is_voluntary_application,
        },
    )
