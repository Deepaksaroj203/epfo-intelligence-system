-- 001_initial_schema.sql
-- PostgreSQL 16 DDL for EPFO Statutory Intelligence System Stage 1 Baseline
-- Includes btree_gist extension, immutable append-only constraints, daterange exclusion, and audit tables.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. SOURCE REGISTRY (Catalog of Tier 1–4 Portals, Manuals, Feeds)
-- ============================================================================
CREATE TABLE IF NOT EXISTS source_registry (
    source_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    trust_tier INT NOT NULL CHECK (trust_tier BETWEEN 1 AND 4),
    url_or_handle TEXT NOT NULL,
    etag_last_modified TEXT,
    consecutive_failures INT NOT NULL DEFAULT 0,
    last_dom_hash TEXT,
    poll_frequency_minutes INT NOT NULL DEFAULT 1440,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_polled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_source_registry_tier ON source_registry (trust_tier, is_active);

-- ============================================================================
-- 2. RAW DOCUMENTS (Immutable Archive keyed by doc_sha256 with PII Redaction)
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_sha256 VARCHAR(64) UNIQUE NOT NULL,
    citation_url TEXT NOT NULL,
    archive_uri TEXT NOT NULL,
    doc_group_id VARCHAR(100),
    language VARCHAR(10) NOT NULL DEFAULT 'en', -- 'en', 'hi', 'bi'
    published_at TIMESTAMPTZ,
    raw_text TEXT,
    redacted_text TEXT NOT NULL, -- PII stripped (PAN, Aadhaar, UAN, phone, party names)
    source_id VARCHAR(100) REFERENCES source_registry(source_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_docs_sha256 ON raw_documents (doc_sha256);
CREATE INDEX IF NOT EXISTS idx_raw_docs_group ON raw_documents (doc_group_id);

-- ============================================================================
-- 3. STATUTORY RULES (Effective-Dated Rates, Ceilings, Eligibility & Penalties)
-- Bitemporal tracking: effective_period (legal) vs recorded_at (system)
-- ============================================================================
CREATE TABLE IF NOT EXISTS statutory_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_key VARCHAR(100) NOT NULL,
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    scope_str TEXT GENERATED ALWAYS AS (scope::text) STORED,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL DEFAULT 'infinity'::date,
    effective_period DATERANGE GENERATED ALWAYS AS (daterange(effective_from, effective_to, '[)')) STORED,
    value_numeric BIGINT, -- Stored in integer paise (e.g. 2500000 = ₹25,000) or basis points (1200 = 12.00%)
    value_type VARCHAR(50) NOT NULL CHECK (value_type IN ('integer_paise', 'basis_points', 'days', 'ratio', 'json_spec', 'boolean')),
    value_json JSONB, -- For complex schemas (e.g. 14B graded damage slab matrices)
    precedence_rank INT NOT NULL DEFAULT 20, -- 5 (SC/HC Override), 10 (e-Gazette), 20 (EPFO HO Circular), 30 (Regional Advisory), 40 (Portal FAQ/KB)
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('announced_pending_gazette', 'scheduled_future', 'active', 'superseded', 'stayed_by_court')),
    is_retroactive BOOLEAN NOT NULL DEFAULT FALSE,
    retroactive_from DATE,
    supersedes_rule_id UUID REFERENCES statutory_rules(rule_id),
    citation_url TEXT NOT NULL,
    doc_sha256 VARCHAR(64) NOT NULL REFERENCES raw_documents(doc_sha256) ON DELETE RESTRICT,
    verbatim_quote TEXT NOT NULL,
    description TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_effective_dates CHECK (effective_to > effective_from),
    CONSTRAINT chk_retroactive_date CHECK (is_retroactive = FALSE OR retroactive_from IS NOT NULL),
    CONSTRAINT uq_active_statutory_rule EXCLUDE USING gist (
        rule_key WITH =,
        scope_str WITH =,
        effective_period WITH &&
    ) WHERE (status IN ('active', 'scheduled_future'))
);

CREATE INDEX IF NOT EXISTS idx_statutory_rules_lookup ON statutory_rules (rule_key, precedence_rank, status);
CREATE INDEX IF NOT EXISTS idx_statutory_rules_period ON statutory_rules USING gist (effective_period);

-- ============================================================================
-- 4. PORTAL FORM REQUIREMENTS (Form & KYC Dependency Graph)
-- ============================================================================
CREATE TABLE IF NOT EXISTS portal_form_requirements (
    requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_code VARCHAR(50) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL DEFAULT 'infinity'::date,
    effective_period DATERANGE GENERATED ALWAYS AS (daterange(effective_from, effective_to, '[)')) STORED,
    required_kyc JSONB NOT NULL, -- e.g. ["aadhaar", "bank_account", "pan"]
    attestation_rules JSONB NOT NULL, -- e.g. {"dsc_required": true, "employer_chain": ["employer", "da", "verifier"]}
    max_claim_threshold_paise BIGINT, -- e.g. 50000000 paise (₹5,00,000)
    approval_tiers JSONB NOT NULL, -- Tier 1 (SSA->AO), Tier 2 (SSA->AO->APFC), Tier 3 (SSA->AO->APFC->OIC)
    dsc_required BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded')),
    citation_url TEXT NOT NULL,
    doc_sha256 VARCHAR(64) NOT NULL REFERENCES raw_documents(doc_sha256) ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_form_dates CHECK (effective_to > effective_from),
    CONSTRAINT uq_active_portal_form EXCLUDE USING gist (
        form_code WITH =,
        effective_period WITH &&
    ) WHERE (status = 'active')
);

CREATE INDEX IF NOT EXISTS idx_portal_form_code ON portal_form_requirements (form_code, status);

-- ============================================================================
-- 5. ROUNDING POLICIES (Versioned Statutory Rounding Rules in Integer Paise)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rounding_policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calc_type VARCHAR(50) NOT NULL, -- 'ECR', '7Q', '14B', 'EPS', 'EDLI', 'ADMIN_CHARGES'
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL DEFAULT 'infinity'::date,
    effective_period DATERANGE GENERATED ALWAYS AS (daterange(effective_from, effective_to, '[)')) STORED,
    rounding_mode VARCHAR(50) NOT NULL CHECK (rounding_mode IN ('half_up_to_rupee', 'round_nearest_rupee', 'truncate_paise', 'exact_paise')),
    rounding_unit_paise INT NOT NULL DEFAULT 100, -- 100 paise = ₹1.00
    min_charge_paise BIGINT NOT NULL DEFAULT 0,
    citation_url TEXT NOT NULL,
    doc_sha256 VARCHAR(64) NOT NULL REFERENCES raw_documents(doc_sha256) ON DELETE RESTRICT,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rounding_dates CHECK (effective_to > effective_from),
    CONSTRAINT uq_active_rounding_policy EXCLUDE USING gist (
        calc_type WITH =,
        effective_period WITH &&
    ) WHERE (status = 'active')
);

CREATE INDEX IF NOT EXISTS idx_rounding_policy_calc ON rounding_policies (calc_type, status);

-- ============================================================================
-- 6. JUDICIAL OVERRIDES (Supreme Court, High Court & CGIT Stays/Judgments)
-- ============================================================================
CREATE TABLE IF NOT EXISTS judicial_overrides (
    override_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_rule_id UUID REFERENCES statutory_rules(rule_id),
    case_citation TEXT NOT NULL,
    court_name VARCHAR(100) NOT NULL,
    jurisdiction_zone VARCHAR(50) NOT NULL DEFAULT 'ALL',
    override_type VARCHAR(50) NOT NULL CHECK (override_type IN ('stayed', 'quashed', 'clarified_restrictive', 'clarified_expansive')),
    override_value_numeric BIGINT,
    override_value_json JSONB,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL DEFAULT 'infinity'::date,
    order_summary TEXT NOT NULL,
    citation_url TEXT NOT NULL,
    doc_sha256 VARCHAR(64) NOT NULL REFERENCES raw_documents(doc_sha256) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_judicial_target ON judicial_overrides (target_rule_id, is_active);

-- ============================================================================
-- 7. PORTAL TROUBLESHOOTING KB (Isolated Tier 4 Error Codes & UI Workarounds)
-- ============================================================================
CREATE TABLE IF NOT EXISTS portal_troubleshooting_kb (
    kb_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_code VARCHAR(100) NOT NULL,
    portal_side VARCHAR(20) NOT NULL CHECK (portal_side IN ('member', 'employer', 'unified')),
    symptom TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    remediation_steps JSONB NOT NULL,
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0.900 CHECK (confidence_score BETWEEN 0.000 AND 1.000),
    source_tier INT NOT NULL DEFAULT 4 CHECK (source_tier BETWEEN 3 AND 4),
    source_reference TEXT,
    verified_by_official BOOLEAN NOT NULL DEFAULT FALSE,
    last_verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_troubleshooting_code ON portal_troubleshooting_kb (error_code, portal_side, confidence_score);

-- ============================================================================
-- 8. RULE CHANGE LOG (Tamper-Evident SHA256 Hash-Chained Audit Trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rule_change_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_number BIGSERIAL UNIQUE NOT NULL,
    target_table VARCHAR(100) NOT NULL,
    rule_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('INSERT', 'UPDATE_SUPERSEDE', 'CANARY_ROLLBACK', 'COURT_OVERRIDE')),
    payload JSONB NOT NULL,
    prev_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL,
    proposed_by VARCHAR(100) NOT NULL,
    approved_by VARCHAR(100) NOT NULL,
    consensus_score NUMERIC(4,3),
    regression_suite_passed BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_change_log_seq ON rule_change_log (sequence_number);

-- ============================================================================
-- 9. API AUDIT LOG (Evaluation Replay, Rule Snapshot Hash & Forensic Replay)
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_audit_log (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    endpoint VARCHAR(100) NOT NULL,
    evaluated_as_of_date DATE NOT NULL,
    rule_snapshot_hash VARCHAR(64) NOT NULL,
    request_payload JSONB NOT NULL,
    response_payload JSONB NOT NULL,
    citation_envelope JSONB NOT NULL,
    execution_time_ms INT NOT NULL,
    client_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_audit_eval_id ON api_audit_log (evaluation_id);
CREATE INDEX IF NOT EXISTS idx_api_audit_as_of ON api_audit_log (evaluated_as_of_date);

-- ============================================================================
-- STORED FUNCTIONS: Deterministic Point-In-Time Lookups with Overrides
-- ============================================================================

-- Function: Check Judicial Overrides for a rule on an event date
CREATE OR REPLACE FUNCTION check_judicial_overrides(
    p_rule_id UUID,
    p_jurisdiction_zone TEXT DEFAULT 'ALL',
    p_event_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    override_id UUID,
    case_citation TEXT,
    court_name VARCHAR(100),
    override_type VARCHAR(50),
    override_value_numeric BIGINT,
    override_value_json JSONB,
    order_summary TEXT,
    citation_url TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        jo.override_id,
        jo.case_citation,
        jo.court_name,
        jo.override_type,
        jo.override_value_numeric,
        jo.override_value_json,
        jo.order_summary,
        jo.citation_url
    FROM judicial_overrides jo
    WHERE jo.target_rule_id = p_rule_id
      AND jo.is_active = TRUE
      AND (jo.jurisdiction_zone = 'ALL' OR jo.jurisdiction_zone = p_jurisdiction_zone)
      AND p_event_date >= jo.effective_from
      AND p_event_date < jo.effective_to
    ORDER BY jo.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: get_rule_as_of(rule_key, scope, event_date)
-- Deterministic parameter resolution strictly ordered by precedence_rank
CREATE OR REPLACE FUNCTION get_rule_as_of(
    p_rule_key TEXT,
    p_scope JSONB DEFAULT '{}'::jsonb,
    p_event_date DATE DEFAULT CURRENT_DATE,
    p_jurisdiction_zone TEXT DEFAULT 'ALL'
)
RETURNS JSONB AS $$
DECLARE
    v_rule statutory_rules%ROWTYPE;
    v_override RECORD;
    v_effective_numeric BIGINT;
    v_effective_json JSONB;
    v_is_overridden BOOLEAN := FALSE;
    v_judicial_notes TEXT := NULL;
    v_citation_url TEXT;
BEGIN
    -- Query active statutory rule matching key and scope on event_date
    -- Highest precedence first (lowest integer rank: 10 e-Gazette > 20 HO Circular > 30 Regional)
    SELECT * INTO v_rule
    FROM statutory_rules sr
    WHERE sr.rule_key = p_rule_key
      AND (p_scope = '{}'::jsonb OR sr.scope @> p_scope OR sr.scope = '{}'::jsonb)
      AND p_event_date >= sr.effective_from
      AND p_event_date < sr.effective_to
      AND sr.status IN ('active', 'scheduled_future')
    ORDER BY sr.precedence_rank ASC, sr.recorded_at DESC
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', 'RULE_NOT_FOUND',
            'rule_key', p_rule_key,
            'scope', p_scope,
            'evaluated_as_of_date', p_event_date
        );
    END IF;

    v_effective_numeric := v_rule.value_numeric;
    v_effective_json := v_rule.value_json;
    v_citation_url := v_rule.citation_url;

    -- Check if modified by Supreme Court, High Court, or CGIT
    SELECT * INTO v_override
    FROM check_judicial_overrides(v_rule.rule_id, p_jurisdiction_zone, p_event_date);

    IF FOUND THEN
        v_is_overridden := TRUE;
        v_judicial_notes := format('Court Override [%s]: %s (%s). %s', 
                                    v_override.override_type, 
                                    v_override.case_citation, 
                                    v_override.court_name, 
                                    v_override.order_summary);
        IF v_override.override_value_numeric IS NOT NULL THEN
            v_effective_numeric := v_override.override_value_numeric;
        END IF;
        IF v_override.override_value_json IS NOT NULL THEN
            v_effective_json := v_override.override_value_json;
        END IF;
        v_citation_url := v_override.citation_url;
    END IF;

    -- Standardized Citation Envelope (Auditable, Deterministic)
    RETURN jsonb_build_object(
        'rule_key', v_rule.rule_key,
        'value_numeric', v_effective_numeric,
        'value_type', v_rule.value_type,
        'value_json', v_effective_json,
        'rule_id', v_rule.rule_id,
        'precedence_rank', CASE WHEN v_is_overridden THEN 5 ELSE v_rule.precedence_rank END,
        'citation_url', v_citation_url,
        'doc_sha256', v_rule.doc_sha256,
        'verbatim_quote', v_rule.verbatim_quote,
        'evaluated_as_of_date', p_event_date,
        'effective_from', v_rule.effective_from,
        'effective_to', v_rule.effective_to,
        'is_retroactive', v_rule.is_retroactive,
        'retroactive_from', v_rule.retroactive_from,
        'is_judicial_override', v_is_overridden,
        'judicial_notes', v_judicial_notes
    );
END;
$$ LANGUAGE plpgsql STABLE;
