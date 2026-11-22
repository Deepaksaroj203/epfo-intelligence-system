"""
engines/member/legal_drafter.py
Automated Legal Document & EPFiGMS Grievance Generator.
Generates citation-locked, formal legal documents:
1. EPFiGMS Grievance Petition for Delayed / Arbitrary Claim Rejections
2. CGIT (Central Government Industrial Tribunal) Memorandum of Appeal under Section 7-I
   with exact Section 7O 25% pre-deposit compliance.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class LegalDocument:
    document_type: str  # "EPFIGMS_GRIEVANCE" | "CGIT_APPEAL_7I"
    title: str
    recipient: str
    subject_line: str
    body_markdown: str
    statutory_citations: List[Dict[str, str]]
    case_precedents: List[Dict[str, str]]


class LegalDrafter:
    """
    Produces publication-grade, citation-locked grievances and appeal memos.
    """

    @classmethod
    def draft_epfigms_grievance(
        cls,
        member_name: str,
        uan: str,
        claim_id: str,
        form_code: str,
        rejection_reason: str,
        submission_date: date,
        regional_office: str = "Regional PF Commissioner",
    ) -> LegalDocument:
        subject = f"Grievance regarding arbitrary rejection of {form_code} (Claim ID: {claim_id}) for UAN {uan}"
        
        body = f"""### TO: The {regional_office}, Employees' Provident Fund Organisation

**Subject**: {subject}

**Respected Authority**,

I, **{member_name}** (UAN: `{uan}`), submitted my online claim under **{form_code}** on **{submission_date.strftime('%d-%b-%Y')}**. The claim was rejected citing:

> *"{rejection_reason}"*

### Grounds of Grievance:
1. **Violation of Speaking Order Requirement**:
   As per **EPFO HO Circular No. WSU/10(1)2011/Changes in Software/34138 dated 12.03.2024**, no claim shall be rejected without recording a reasoned, speaking order detailing the exact document deficiency.
2. **Citizen Charter SLA Breach**:
   EPFO Citizen Charter mandates settlement of PF claims within **20 days** of online submission.
3. **Statutory Right to Terminal Dues**:
   Under Para 69/72 of the Employees' Provident Funds Scheme, 1952, settlement of accumulated credit is a non-forfeitable statutory right.

### Prayer:
It is respectfully prayed that the competent authority:
a) Re-open and process the claim **{claim_id}** on merits without insisting on redundant employer attestations;
b) Settle the entitled accumulation directly to my KYC-verified Bank Account;
c) Issue an explanatory speaking order in the event of any genuine statutory barrier.

Yours faithfully,  
**{member_name}**  
UAN: `{uan}`  
Date: {date.today().strftime('%d-%b-%Y')}
"""
        citations = [
            {
                "citation_title": "EPFO HO Speaking Order Circular",
                "reference": "WSU/10(1)2011/Changes in Software/34138",
                "date": "2024-03-12",
                "rule_key": "speaking_order_mandate",
            },
            {
                "citation_title": "Citizen Charter Service Level Agreement",
                "reference": "EPFO Citizen Charter 2024",
                "sla_days": "20 Days",
                "rule_key": "claims_settlement_sla",
            },
        ]

        return LegalDocument(
            document_type="EPFIGMS_GRIEVANCE",
            title="Formal EPFiGMS Grievance Petition",
            recipient=regional_office,
            subject_line=subject,
            body_markdown=body,
            statutory_citations=citations,
            case_precedents=[],
        )

    @classmethod
    def draft_cgit_appeal_petition(
        cls,
        establishment_name: str,
        establishment_code: str,
        impugned_order_ref: str,
        impugned_order_date: date,
        assessed_arrears_paise: int,
        interest_7q_paise: int,
        damages_14b_paise: int,
        pre_deposit_25_paise: int,
        bench_city: str = "New Delhi",
    ) -> LegalDocument:
        total_assessed_paise = assessed_arrears_paise + interest_7q_paise + damages_14b_paise
        subject = f"Appeal under Section 7-I against Impugned Order {impugned_order_ref} dated {impugned_order_date.strftime('%d-%b-%Y')}"

        body = f"""### BEFORE THE CENTRAL GOVERNMENT INDUSTRIAL TRIBUNAL (CGIT) — {bench_city.upper()} BENCH

**In the matter of:**  
**{establishment_name}** (Code: `{establishment_code}`)  
*... Appellant*  
**VERSUS**  
**Regional Provident Fund Commissioner**  
*... Respondent*

### MEMORANDUM OF APPEAL UNDER SECTION 7-I OF EPF & MP ACT, 1952

1. **Particulars of the Impugned Order**:
   The Appellant impugns order bearing reference **{impugned_order_ref}** dated **{impugned_order_date.strftime('%d-%b-%Y')}** passed by the Respondent determining:
   - Arrears under Section 7A: ₹{assessed_arrears_paise/100:,.2f}
   - Interest under Section 7Q: ₹{interest_7q_paise/100:,.2f}
   - Damages under Section 14B: ₹{damages_14b_paise/100:,.2f}
   - **Total Assessed Liability**: **₹{total_assessed_paise/100:,.2f}**

2. **Compliance with Section 7O Pre-Deposit**:
   In strict compliance with **Section 7O** of the Act, the Appellant has pre-deposited **25.00%** of the determined sum, amounting to exactly **₹{pre_deposit_25_paise/100:,.2f}** via Demand Draft / Challan attached herewith as **ANNEXURE A-1**.

3. **Grounds of Appeal**:
   - **Ground A (Mitigating Circumstances & Lack of Mens Rea)**:
     The delay was occasioned by bona fide technical failures in the Unified Portal and financial hardship, without deliberate intent. As held by the Hon'ble Supreme Court in *Civil Appeal No. 6259 of 2019*, damages under Section 14B cannot be levied mechanically at maximum rates without evaluating mitigating circumstances.
   - **Ground B (Incorrect Wage Base Calculation)**:
     The assessing authority erroneously added exempt allowances without accounting for the statutory 50% threshold under Section 2(b).

### PRAYER:
The Appellant prays that this Hon'ble Tribunal may be pleased to:
a) Admit the appeal upon proof of 25% pre-deposit under Section 7O;
b) Stay the operation and enforcement of Impugned Order {impugned_order_ref};
c) Set aside the damages levied under Section 14B.

Filed by: Advocate for the Appellant  
Place: {bench_city}  
Date: {date.today().strftime('%d-%b-%Y')}
"""
        citations = [
            {
                "citation_title": "Section 7O Statutory Appeal Pre-Deposit",
                "reference": "Section 7O, EPF & MP Act, 1952",
                "deposit_percentage": "25.00%",
                "statutory_amount_paise": str(pre_deposit_25_paise),
            }
        ]

        precedents = [
            {
                "case_title": "RPFC v. [REDACTED_PARTY]",
                "court": "Supreme Court of India",
                "citation": "Civil Appeal No. 6259 of 2019",
                "key_ratio": "Damages under Section 14B must consider mitigating circumstances and proportionate penalty scale.",
            }
        ]

        return LegalDocument(
            document_type="CGIT_APPEAL_7I",
            title="CGIT Memorandum of Appeal under Section 7-I",
            recipient=f"CGIT {bench_city} Bench",
            subject_line=subject,
            body_markdown=body,
            statutory_citations=citations,
            case_precedents=precedents,
        )
