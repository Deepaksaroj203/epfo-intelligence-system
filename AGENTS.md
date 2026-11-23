# EPFO Intelligence System — Agent Engineering & Architectural Rules

## 1. System Overview & Invariants
- **Domain**: Production-grade statutory compliance engine for Indian EPFO & Labour Laws covering Member-Side and Employer-Side workflows.
- **Stack**: FastAPI, PostgreSQL 16 (`btree_gist` + `pgvector`), Redis 7, Celery, Playwright, Uvicorn.
- **Strict Invariants**:
  1. **Zero Hardcoded Law & Zero LLM Math**: All statutory rates, wage ceilings, 7Q/14B damage tables, and thresholds MUST be fetched from PostgreSQL (`statutory_rules`, `rounding_policies`) via `get_rule_as_of()`. All math is executed strictly in integer paise.
  2. **Bitemporal & Append-Only**: Never mutate or delete historical rules. Use `daterange` with `EXCLUDE USING gist`, `supersedes_rule_id`, `is_retroactive`, and hash-chained `rule_change_log`.
  3. **Strict Source Precedence**: SC/HC judgments > e-Gazette > EPFO HO Circular > Regional Advisory > Portal FAQ.
  4. **PII Sanitization**: Redact UAN, Aadhaar, PAN, phone numbers, and member names before vector embedding or indexing.

---

## 2. Integrated Skill Routing Decision Matrix
The repository is equipped with specialized agent playbooks in `.agents/skills/`. Agents operating in this repository must route tasks according to this matrix:

| Task Type | Primary Skills to Activate | Action & Quality Gate |
|---|---|---|
| **RAG & Statutory Precedents** | `rag-engineer`, `rag-implementation` | Enforce hybrid vector search (cosine similarity $\ge 0.82$), bitemporal date filtering (`as_of_date`), strict citation-locking, and zero hallucination. |
| **Autonomous Ingestion & Crawlers** | `ai-agents-architect`, `langgraph` | Build multi-tier crawlers, conditional `304 Not Modified` probes, dual-extractor consensus ($\ge 0.98$), and shadow-DB validation. |
| **Regression & Golden Testing** | `agent-evaluation`, `test-driven-development` | Run boundary-date tests against 2014 & 2026 regimes, wage ceiling transitions (₹15,000 $\rightarrow$ ₹25,000), and verify exit code 0. |
| **Token Efficiency & Bot Performance** | `prompt-caching`, `context-window-management` | Optimize system prompts for Telegram Bot (`bot/telegram_bot.py`) and Copilot (`api/copilot.py`) with cached statutory schemas. |
| **API Contract & Schema Hardening** | `fastapi-pro`, `database-design`, `api-patterns` | Enforce Pydantic V2 models, integer paise types, deterministic response envelopes, and OpenAPI specs. |
| **Bugs / Broken Pipelines** | `systematic-debugging` | Perform root-cause diagnosis using logs (`logs/`), database traces, and compiler errors without speculative code changes. |

---

## 3. Mandatory Verification Gate
Never declare any feature or bug fix complete without running:
```powershell
python -m pytest tests/golden/ -v
```
All statutory invariant tests and boundary tests must pass with 0 failures before merging.
