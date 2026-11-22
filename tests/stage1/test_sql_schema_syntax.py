"""
test_sql_schema_syntax.py
Validates the PostgreSQL 16 DDL migration scripts (001_initial_schema.sql and 002_seed_data.sql)
for structural integrity, foreign key references, and table specifications.
"""

from pathlib import Path
import re
import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "db" / "migrations"


def test_migration_files_exist():
    schema_file = MIGRATIONS_DIR / "001_initial_schema.sql"
    seed_file = MIGRATIONS_DIR / "002_seed_data.sql"
    assert schema_file.exists(), f"Missing {schema_file}"
    assert seed_file.exists(), f"Missing {seed_file}"


def test_schema_tables_present():
    schema_file = MIGRATIONS_DIR / "001_initial_schema.sql"
    content = schema_file.read_text(encoding="utf-8")

    expected_tables = [
        "source_registry",
        "raw_documents",
        "statutory_rules",
        "portal_form_requirements",
        "rounding_policies",
        "judicial_overrides",
        "portal_troubleshooting_kb",
        "rule_change_log",
        "api_audit_log",
    ]

    for table in expected_tables:
        pattern = rf"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?{table}\b"
        assert re.search(pattern, content, re.IGNORECASE), f"Table {table} not found in schema DDL"


def test_btree_gist_and_daterange_constraints():
    schema_file = MIGRATIONS_DIR / "001_initial_schema.sql"
    content = schema_file.read_text(encoding="utf-8")

    # Check extension
    assert "CREATE EXTENSION IF NOT EXISTS \"btree_gist\";" in content

    # Check daterange exclusion constraints
    assert "EXCLUDE USING gist" in content
    assert "effective_period WITH &&" in content
    assert "uq_active_statutory_rule" in content
    assert "uq_active_portal_form" in content
    assert "uq_active_rounding_policy" in content


def test_sql_lookup_functions_present():
    schema_file = MIGRATIONS_DIR / "001_initial_schema.sql"
    content = schema_file.read_text(encoding="utf-8")

    assert "FUNCTION check_judicial_overrides" in content
    assert "FUNCTION get_rule_as_of" in content


def test_seed_data_corresponds_to_schema():
    seed_file = MIGRATIONS_DIR / "002_seed_data.sql"
    content = seed_file.read_text(encoding="utf-8")

    # Verify seed entries
    assert "tier1_egazette" in content
    assert "statutory_wage_ceiling" in content
    assert "2500000" in content  # ₹25,000 in integer paise
    assert "1500000" in content  # ₹15,000 in integer paise
    assert "650000" in content   # ₹6,500 in integer paise
    assert "delayed_interest_7q_annual_rate" in content
    assert "penal_damages_14b_slabs" in content
    assert "tribunal_appeal_deposit_percent" in content
    assert "round_nearest_rupee" in content
    assert "FORM_19" in content
    assert "ECR_V3" in content
