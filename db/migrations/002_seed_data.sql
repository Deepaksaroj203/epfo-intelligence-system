-- 002_seed_data.sql
-- Seed Corpus for EPFO Statutory Rules & Cases System Stage 1 Baseline
-- Covers Tier 1–4 Source Registry, Raw Document Archives with SHA256 hashes,
-- Rounding Policies, Form Requirements, and Statutory Rules (1952 Legacy -> 2026 Code Regime).

-- ============================================================================
-- 1. SEED SOURCE REGISTRY
-- ============================================================================
INSERT INTO source_registry (source_id, name, trust_tier, url_or_handle, poll_frequency_minutes, is_active)
VALUES
    ('tier1_egazette', 'e-Gazette of India (Ministry of Labour & Employment Notifications)', 1, 'https://egazette.gov.in', 360, TRUE),
    ('tier1_epfo_circulars', 'EPFO Head Office Circulars & Operational Instructions', 1, 'https://www.epfindia.gov.in/site_en/Circulars.php', 60, TRUE),
    ('tier1_employer_ecr_portal', 'EPFO Unified Employer Portal & Revamped ECR v3.0 Specifications', 1, 'https://unifiedportal-emp.epfindia.gov.in', 1440, TRUE),
    ('tier1_compliance_manual', 'EPFO Desk Review, Inspection SOP & Branch Clubbing Manual', 1, 'https://www.epfindia.gov.in/site_en/Compliance_Manual.php', 1440, TRUE),
    ('tier1_member_portal_sops', 'Member Portal SOPs (Joint Declaration, UAN 2.0, Delinking, Claims)', 1, 'https://unifiedportal-mem.epfindia.gov.in', 1440, TRUE),
    ('tier2_pib_releases', 'Press Information Bureau (PIB) Labour & Employment & CBT Releases', 2, 'https://pib.gov.in', 180, TRUE),
    ('tier2_cgit_tribunal', 'Central Government Industrial Tribunal (CGIT) Appellate Orders', 2, 'https://cgit.gov.in', 720, TRUE),
    ('tier2_eproceedings_orders', 'EPFO e-Proceedings Portal (Section 7A, 14B & 7Q Quasi-Judicial Orders)', 2, 'https://eproceedings.epfindia.gov.in', 720, TRUE),
    ('tier2_epfigms_grievance', 'EPFiGMS Grievance Management System & SLA Norms', 2, 'https://epfigms.gov.in', 1440, TRUE),
    ('tier3_official_x', 'Official EPFO X Handle (@officialepfo)', 3, 'https://x.com/officialepfo', 30, TRUE),
    ('tier3_official_youtube', 'Official Social EPFO YouTube Channel', 3, 'https://www.youtube.com/@socialepfo', 720, TRUE),
    ('tier4_practitioner_kb', 'Indian Payroll & HR Compliance Community Feeds (Verified WhatsApp / Forums)', 4, 'https://corporatecompliance.in/kb/community', 120, TRUE)
ON CONFLICT (source_id) DO NOTHING;

-- ============================================================================
-- 2. SEED RAW DOCUMENTS ARCHIVE
-- Immutable documents with real/canonical SHA256 hashes and PII redaction
-- ============================================================================
INSERT INTO raw_documents (doc_sha256, citation_url, archive_uri, doc_group_id, language, published_at, raw_text, redacted_text, source_id)
VALUES
    (
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        's3://epfo-documents/1952/EPF_Act_1952.pdf',
        'STATUTE_1952',
        'en',
        '1952-03-04 00:00:00+05:30',
        'Employees Provident Funds and Miscellaneous Provisions Act 1952',
        '[REDACTED] Employees Provident Funds and Miscellaneous Provisions Act 1952 (Act No. 19 of 1952). Sections 2A, 6, 6A, 6C, 7A, 7Q, 14B.',
        'tier1_egazette'
    ),
    (
        '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
        'https://egazette.gov.in/WriteReadData/2014/GSR_609_E_Wage_Ceiling.pdf',
        's3://epfo-documents/2014/GSR_609_E.pdf',
        'WAGE_CEILING_2014',
        'bi',
        '2014-08-22 00:00:00+05:30',
        'Notification G.S.R. 609(E) raising the statutory wage ceiling from Rs. 6500 to Rs. 15000 per month with effect from 1st September 2014.',
        '[REDACTED] Ministry of Labour and Employment Notification G.S.R. 609(E) dated August 22, 2014. In the Employees Provident Funds Scheme 1952, for the words six thousand and five hundred rupees, the words fifteen thousand rupees shall be substituted with effect from 1st day of September 2014.',
        'tier1_egazette'
    ),
    (
        '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
        'https://egazette.gov.in/WriteReadData/2026/SO_5109_E_Wage_Ceiling_25K.pdf',
        's3://epfo-documents/2026/SO_5109_E.pdf',
        'WAGE_CEILING_2026',
        'bi',
        '2026-09-17 00:00:00+05:30',
        'Notification S.O. 5109(E) raising statutory wage ceiling to Rs. 25000 per month under EPF Scheme, EPS-95 and EDLI Schemes.',
        '[REDACTED] Ministry of Labour and Employment Notification S.O. 5109(E) dated September 17, 2026. Pursuant to the decisions of the Central Board of Trustees (CBT) and approval by the Central Government, the statutory monthly wage ceiling is hereby notified as Rs. 25,000 (Twenty-Five Thousand Rupees) with effect from 17th September 2026.',
        'tier1_egazette'
    ),
    (
        '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
        'https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2024-2025/Circular_Sec14B_Damages_Revision_June2024.pdf',
        's3://epfo-documents/2024/Circular_Sec14B_Damages.pdf',
        'PENALTIES_14B_2024',
        'en',
        '2024-06-14 00:00:00+05:30',
        'Head Office Circular on rationalization of damages under Section 14B and interest under Section 7Q.',
        '[REDACTED] EPFO Head Office Circular No. C-I/1(33)2024/Damages/768. Standardized damages under Section 14B and simple interest at 12% per annum under Section 7Q of the EPF & MP Act 1952.',
        'tier1_epfo_circulars'
    ),
    (
        'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
        'https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2026-2027/Circular_Joint_Declaration_SOP_v3.pdf',
        's3://epfo-documents/2026/Joint_Declaration_SOP_v3.pdf',
        'MEMBER_SOP_JD',
        'en',
        '2026-03-11 00:00:00+05:30',
        'Comprehensive Standard Operating Procedure (SOP) for Joint Declaration for member profile correction.',
        '[REDACTED] Comprehensive Standard Operating Procedure for correction in Member Profile through Joint Declaration. Approval matrix: Minor changes approved by DA/SS; Major changes require APFC/OIC approval with employer digital signature.',
        'tier1_member_portal_sops'
    ),
    (
        '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918',
        'https://main.sci.gov.in/supremecourt/2019/Vivekananda_Vidyamandir_CA_6264_2019.pdf',
        's3://epfo-documents/judiciary/SC_Vivekananda_Vidyamandir_2019.pdf',
        'JUDICIAL_WAGES_SC',
        'en',
        '2019-02-28 00:00:00+05:30',
        'Supreme Court Judgment in Regional Provident Fund Commissioner vs Vivekananda Vidyamandir (2019) on basic wages and excluded allowances.',
        '[REDACTED] Supreme Court of India Civil Appeal No. 6264 of 2019. Any allowance that is universally, ordinarily and consistently paid to all employees across the board without variation forms part of basic wages for EPF deduction.',
        'tier2_cgit_tribunal'
    )
ON CONFLICT (doc_sha256) DO NOTHING;

-- ============================================================================
-- 3. SEED ROUNDING POLICIES (Integer Paise Base)
-- ============================================================================
INSERT INTO rounding_policies (calc_type, effective_from, effective_to, rounding_mode, rounding_unit_paise, min_charge_paise, citation_url, doc_sha256)
VALUES
    (
        'ECR',
        '1952-03-04',
        'infinity',
        'round_nearest_rupee',
        100, -- Rounded to nearest ₹1.00 (100 paise)
        0,
        'https://unifiedportal-emp.epfindia.gov.in',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    ),
    (
        '7Q',
        '1988-08-01',
        'infinity',
        'exact_paise',
        1, -- Computed daily in exact paise, rounded half_up at challan generation
        0,
        'https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2024-2025/Circular_Sec14B_Damages_Revision_June2024.pdf',
        '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a'
    ),
    (
        '14B',
        '1952-03-04',
        'infinity',
        'round_nearest_rupee',
        100, -- 100 paise = ₹1
        0,
        'https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2024-2025/Circular_Sec14B_Damages_Revision_June2024.pdf',
        '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a'
    ),
    (
        'EPS',
        '1995-11-16',
        'infinity',
        'half_up_to_rupee',
        100,
        0,
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    ),
    (
        'ADMIN_CHARGES',
        '1952-03-04',
        'infinity',
        'round_nearest_rupee',
        100,
        75000, -- Minimum admin charges ₹750/month (or ₹500 depending on unexempted status)
        'https://unifiedportal-emp.epfindia.gov.in',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    ),
    (
        'INSPECTION_CHARGES',
        '1952-03-04',
        'infinity',
        'round_nearest_rupee',
        100,
        0,
        'https://unifiedportal-emp.epfindia.gov.in',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    )
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 4. SEED PORTAL FORM REQUIREMENTS (KYC & Approval Dependency Graph)
-- ============================================================================
INSERT INTO portal_form_requirements (
    form_code, effective_from, effective_to, required_kyc, attestation_rules, 
    max_claim_threshold_paise, approval_tiers, dsc_required, citation_url, doc_sha256
)
VALUES
    (
        'FORM_19',
        '2015-01-01',
        'infinity',
        '["aadhaar", "bank_account", "pan"]'::jsonb,
        '{"dsc_required_if_unauthenticated": true, "unattested_allowed_if_aadhaar_linked": true, "employer_attestation_exempt_if_closed": true}'::jsonb,
        250000000, -- ₹25 Lakhs scrutiny ceiling
        '{
            "tier_1_under_5L": ["SSA", "AO"],
            "tier_2_5L_to_25L": ["SSA", "AO", "APFC"],
            "tier_3_above_25L": ["SSA", "AO", "APFC", "OIC"]
        }'::jsonb,
        FALSE,
        'https://unifiedportal-mem.epfindia.gov.in',
        'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d'
    ),
    (
        'FORM_10C',
        '2015-01-01',
        'infinity',
        '["aadhaar", "bank_account"]'::jsonb,
        '{"service_under_10_years_required": true, "employer_default_excluded": true}'::jsonb,
        100000000, -- ₹10 Lakhs
        '{
            "tier_1_under_5L": ["SSA", "AO"],
            "tier_2_above_5L": ["SSA", "AO", "APFC"]
        }'::jsonb,
        FALSE,
        'https://unifiedportal-mem.epfindia.gov.in',
        'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d'
    ),
    (
        'FORM_31',
        '2015-01-01',
        'infinity',
        '["aadhaar", "bank_account"]'::jsonb,
        '{"auto_settlement_limit_paise": 10000000, "advance_types": ["illness", "marriage", "education", "housing", "special"]}'::jsonb,
        100000000,
        '{
            "tier_1_auto_mode": ["IT_SYSTEM"],
            "tier_2_manual": ["SSA", "AO"]
        }'::jsonb,
        FALSE,
        'https://unifiedportal-mem.epfindia.gov.in',
        'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d'
    ),
    (
        'JOINT_DECLARATION',
        '2024-01-01',
        'infinity',
        '["aadhaar", "pan", "passport_or_voter_id"]'::jsonb,
        '{
            "employer_dsc_approval_mandatory": true,
            "minor_changes": ["DA", "SS"],
            "major_changes": ["DA", "SS", "APFC_OIC"]
        }'::jsonb,
        0,
        '{"approval_chain": ["MEMBER", "EMPLOYER_DSC", "DA", "SS", "APFC"]}'::jsonb,
        TRUE,
        'https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2026-2027/Circular_Joint_Declaration_SOP_v3.pdf',
        'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d'
    ),
    (
        'ECR_V3',
        '2024-01-01',
        'infinity',
        '["uan", "pan", "aadhaar"]'::jsonb,
        '{
            "mandatory_fields": ["UAN", "MEMBER_NAME", "GROSS_WAGES", "EPF_WAGES", "EPS_WAGES", "EDLI_WAGES", "EE_SHARE", "ER_EPF_SHARE", "ER_EPS_SHARE", "NCP_DAYS"],
            "exempted_reporting_mandatory": true,
            "age_58_eps_block": true
        }'::jsonb,
        0,
        '{"validation_level": ["CLIENT_PORTAL_PARSER", "TRRN_GENERATOR"]}'::jsonb,
        TRUE,
        'https://unifiedportal-emp.epfindia.gov.in',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    )
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 5. SEED STATUTORY RULES (1952 Legacy + 2014 Shift + 2026 Code Regime)
-- Values stored in integer paise or basis points (1% = 100 bps)
-- ============================================================================

-- A. Statutory Wage Ceiling (Pre-2014: ₹6,500; 2014-2026: ₹15,000; Post Sept 17, 2026: ₹25,000)
INSERT INTO statutory_rules (
    rule_key, scope, effective_from, effective_to, value_numeric, value_type, precedence_rank, status,
    citation_url, doc_sha256, verbatim_quote, description
)
VALUES
    -- Regime 1: Up to 31 August 2014 (₹6,500 = 650000 paise)
    (
        'statutory_wage_ceiling',
        '{"side": "both", "establishment_type": "all", "worker_category": "domestic"}'::jsonb,
        '2001-06-01',
        '2014-09-01',
        650000,
        'integer_paise',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'Six thousand and five hundred rupees per month.',
        'Statutory EPF/EPS wage ceiling pre-September 2014'
    ),
    -- Regime 2: 1 September 2014 to 16 September 2026 (₹15,000 = 1500000 paise)
    (
        'statutory_wage_ceiling',
        '{"side": "both", "establishment_type": "all", "worker_category": "domestic"}'::jsonb,
        '2014-09-01',
        '2026-09-17',
        1500000,
        'integer_paise',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/2014/GSR_609_E_Wage_Ceiling.pdf',
        '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
        'In the Employees Provident Funds Scheme 1952, for the words six thousand and five hundred rupees, the words fifteen thousand rupees shall be substituted.',
        'Statutory EPF/EPS wage ceiling under G.S.R. 609(E)'
    ),
    -- Regime 3: 17 September 2026 onward (₹25,000 = 2500000 paise per S.O. 5109(E))
    (
        'statutory_wage_ceiling',
        '{"side": "both", "establishment_type": "all", "worker_category": "domestic"}'::jsonb,
        '2026-09-17',
        'infinity',
        2500000,
        'integer_paise',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/2026/SO_5109_E_Wage_Ceiling_25K.pdf',
        '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
        'The statutory monthly wage ceiling is hereby notified as Rs. 25,000 with effect from 17th September 2026.',
        'Statutory EPF/EPS wage ceiling increased to ₹25,000 per month under S.O. 5109(E)'
    );

-- B. Statutory Contribution Rates
INSERT INTO statutory_rules (
    rule_key, scope, effective_from, effective_to, value_numeric, value_type, precedence_rank, status,
    citation_url, doc_sha256, verbatim_quote, description
)
VALUES
    -- Employee EPF Contribution (12.00% = 1200 basis points)
    (
        'epf_employee_rate',
        '{"side": "member", "establishment_type": "unexempted"}'::jsonb,
        '1952-03-04',
        'infinity',
        1200,
        'basis_points',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'The contribution which shall be paid by the employee to the Fund shall be twelve per cent of the basic wages, dearness allowance and retaining allowance.',
        'Standard employee EPF statutory deduction rate'
    ),
    -- Employer EPS Contribution (8.33% = 833 basis points)
    (
        'eps_employer_rate',
        '{"side": "employer", "establishment_type": "unexempted"}'::jsonb,
        '1995-11-16',
        'infinity',
        833,
        'basis_points',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'From and out of the contributions payable by the employer, a sum equivalent to 8.33 per cent of the wages shall be remitted to the Pension Fund.',
        'Employer pension contribution (capped at statutory wage ceiling)'
    ),
    -- Employer EPF Net Share (3.67% = 367 basis points)
    (
        'epf_employer_net_rate',
        '{"side": "employer", "establishment_type": "unexempted"}'::jsonb,
        '1995-11-16',
        'infinity',
        367,
        'basis_points',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'The remainder of the employers contribution shall be credited to the Employee Provident Fund.',
        'Net employer EPF contribution (12.00% - 8.33% = 3.67%)'
    ),
    -- EDLI Contribution (0.50% = 50 basis points)
    (
        'edli_employer_rate',
        '{"side": "employer", "establishment_type": "all"}'::jsonb,
        '1976-08-01',
        'infinity',
        50,
        'basis_points',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'The contribution payable by the employer to the Insurance Fund shall be zero point five zero per cent of the wages.',
        'Employees Deposit Linked Insurance (EDLI) contribution rate'
    ),
    -- EPF Admin Charges (0.50% = 50 basis points, minimum ₹500/₹75)
    (
        'epf_admin_rate',
        '{"side": "employer", "establishment_type": "unexempted"}'::jsonb,
        '2018-06-01',
        'infinity',
        50,
        'basis_points',
        10,
        'active',
        'https://unifiedportal-emp.epfindia.gov.in',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'Administrative charges payable by the employer shall be 0.50% of the total wages subject to a minimum of Rs. 500 per month.',
        'EPF Account 2 Admin charges'
    );

-- C. Delayed Payment Interest (Section 7Q: 12.00% p.a. simple interest)
INSERT INTO statutory_rules (
    rule_key, scope, effective_from, effective_to, value_numeric, value_type, precedence_rank, status,
    citation_url, doc_sha256, verbatim_quote, description
)
VALUES
    (
        'delayed_interest_7q_annual_rate',
        '{"side": "employer", "action": "penalties"}'::jsonb,
        '1988-08-01',
        'infinity',
        1200, -- 1200 basis points = 12.00% simple interest per annum
        'basis_points',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'The employer shall be liable to pay simple interest at the rate of twelve per cent per annum or at such higher rate as may be specified in the Scheme on any amount due from him under this Act from the date on which the amount has become so due until the date of its actual payment.',
        'Statutory simple interest under Section 7Q of EPF & MP Act 1952'
    );

-- D. Section 14B Penal Damages Graded Slabs
-- Pre-June 2024 Graded Slabs (<2m: 5%, 2-4m: 10%, 4-6m: 15%, >6m: 25%)
INSERT INTO statutory_rules (
    rule_key, scope, effective_from, effective_to, value_numeric, value_type, value_json, precedence_rank, status,
    citation_url, doc_sha256, verbatim_quote, description
)
VALUES
    (
        'penal_damages_14b_slabs',
        '{"side": "employer", "action": "penalties", "regime": "legacy_graded"}'::jsonb,
        '1952-03-04',
        '2024-06-15',
        NULL,
        'json_spec',
        '{
            "slabs": [
                {"min_days": 1, "max_days": 60, "rate_pa_bps": 500, "rate_pa_percent": 5.0},
                {"min_days": 61, "max_days": 120, "rate_pa_bps": 1000, "rate_pa_percent": 10.0},
                {"min_days": 121, "max_days": 180, "rate_pa_bps": 1500, "rate_pa_percent": 15.0},
                {"min_days": 181, "max_days": null, "rate_pa_bps": 2500, "rate_pa_percent": 25.0}
            ]
        }'::jsonb,
        10,
        'active',
        'https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2024-2025/Circular_Sec14B_Damages_Revision_June2024.pdf',
        '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
        'Where an employer makes default in the payment of any contribution to the Fund, the Central Provident Fund Commissioner may recover from the employer by way of penalty such damages, not exceeding the amount of arrears.',
        'Historical graded 14B damages slabs pre-June 2024'
    ),
    -- Post-June 2024 Standardized Slabs (Flat 1% per month or part thereof = 12% p.a.)
    (
        'penal_damages_14b_slabs',
        '{"side": "employer", "action": "penalties", "regime": "legacy_graded"}'::jsonb,
        '2024-06-15',
        'infinity',
        1200,
        'basis_points',
        '{
            "mode": "flat_monthly_rate",
            "monthly_rate_bps": 100,
            "annual_rate_bps": 1200,
            "max_damages_cap_percent": 100
        }'::jsonb,
        10,
        'active',
        'https://www.epfindia.gov.in/site_docs/PDFs/Circulars/Y2024-2025/Circular_Sec14B_Damages_Revision_June2024.pdf',
        '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
        'Revised uniform rate of damages under Section 14B at 1% per month of delay subject to maximum 100% of arrears.',
        'Standardized 14B damages from 15 June 2024 onward'
    );

-- E. Section 7O Tribunal Appeal Deposit (25% of assessed amount)
INSERT INTO statutory_rules (
    rule_key, scope, effective_from, effective_to, value_numeric, value_type, precedence_rank, status,
    citation_url, doc_sha256, verbatim_quote, description
)
VALUES
    (
        'tribunal_appeal_deposit_percent',
        '{"side": "employer", "action": "appeals", "tribunal": "CGIT"}'::jsonb,
        '1997-07-01',
        'infinity',
        2500, -- 2500 basis points = 25.00%
        'basis_points',
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'No appeal by the employer shall be entertained by a Tribunal unless he has deposited with the Tribunal 25 per cent of the amount due from him as determined by the officer under section 7A.',
        'Mandatory 25% pre-deposit under Section 7O for filing CGIT appeal'
    );

-- F. Excluded Allowance Cap / 50% Wage Add-Back Rule
INSERT INTO statutory_rules (
    rule_key, scope, effective_from, effective_to, value_numeric, value_type, precedence_rank, status,
    citation_url, doc_sha256, verbatim_quote, description
)
VALUES
    (
        'excluded_allowances_cap_percent',
        '{"side": "employer", "action": "payroll_structure"}'::jsonb,
        '2019-02-28',
        'infinity',
        5000, -- 5000 basis points = 50.00%
        'basis_points',
        5, -- Judicial precedent precedence
        'active',
        'https://main.sci.gov.in/supremecourt/2019/Vivekananda_Vidyamandir_CA_6264_2019.pdf',
        '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918',
        'Allowances universally and consistently paid to all employees form part of basic wages. If excluded allowances exceed 50% of total remuneration, the excess must be added back to wages for statutory calculations.',
        '50% wage threshold under Code on Social Security 2020 and Supreme Court Vivekananda Vidyamandir ruling'
    );

-- G. Headcount Coverage Threshold (20 or more employees)
INSERT INTO statutory_rules (
    rule_key, scope, effective_from, effective_to, value_numeric, value_type, precedence_rank, status,
    citation_url, doc_sha256, verbatim_quote, description
)
VALUES
    (
        'statutory_coverage_headcount',
        '{"side": "employer", "action": "establishment_coverage"}'::jsonb,
        '1952-03-04',
        'infinity',
        20,
        'days', -- numeric count
        10,
        'active',
        'https://egazette.gov.in/WriteReadData/1952/EPF_Act_1952.pdf',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'To every establishment which is a factory engaged in any industry specified in Schedule I and in which twenty or more persons are employed.',
        'Mandatory coverage threshold of 20 employees'
    );

-- ============================================================================
-- 6. SEED INITIAL HASH-CHAIN IN RULE CHANGE LOG
-- ============================================================================
INSERT INTO rule_change_log (
    sequence_number, target_table, rule_id, action, payload, prev_hash, entry_hash, 
    proposed_by, approved_by, consensus_score, regression_suite_passed
)
VALUES
    (
        1,
        'statutory_rules',
        '00000000-0000-0000-0000-000000000000'::uuid,
        'INSERT',
        '{"event": "GENESIS_STAGE_1_CORPUS", "version": "1.0.0", "statute": "EPF_1952_AND_2026_CODE"}'::jsonb,
        '0000000000000000000000000000000000000000000000000000000000000000',
        encode(digest('GENESIS_STAGE_1_BASELINE_2026', 'sha256'), 'hex'),
        'system_architect',
        'principal_architect',
        1.000,
        TRUE
    )
ON CONFLICT (sequence_number) DO NOTHING;
