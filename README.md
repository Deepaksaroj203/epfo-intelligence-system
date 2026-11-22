# EPFO Statutory Rules & Cases Intelligence System

> **Autonomous, Self-Updating Statutory Intelligence Platform covering both Member-Side and Employer-Side Compliance in India.**

[![Tests](https://img.shields.io/badge/pytest-65%20passed-brightgreen.svg)]()
[![Architecture](https://img.shields.io/badge/PostgreSQL-16%20%7C%20btree__gist%20%7C%20pgvector-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20Ready-009688.svg)]()
[![Zero LLM Math](https://img.shields.io/badge/Statutory%20Math-Deterministic%20Integer%20Paise-red.svg)]()

---

## 🏛️ Non-Negotiable Architectural Rules

1. **Zero Hardcoded Law & Zero LLM Math**: All statutory rates, ceilings, interest (Section 7Q), damages (Section 14B), and rounding modes live in PostgreSQL (`statutory_rules`, `rounding_policies`) queried via `get_rule_as_of(rule_key, scope, event_date)` in **integer paise**. LLMs are strictly restricted to parsing raw PDFs into candidate diffs.
2. **Bitemporal & Append-Only**: PostgreSQL `daterange` with `btree_gist` exclusion constraints (`EXCLUDE USING gist`) prevent overlapping rule periods. All promotions and rollbacks are recorded with SHA-256 hash-chains in `rule_change_log`.
3. **Strict Source Precedence**: Supreme Court / High Court (`judicial_overrides`, rank 5) > e-Gazette (rank 10) > EPFO Head Office Circular (rank 20) > Regional Advisory (rank 30) > Portal FAQ / Community KB (rank 40).
4. **Autonomous Confidence-Gated Pipeline**:
   - **06:00 IST**: Stage 3 full sweep with 5-minute conditional HTTP 304 probes on `.gov.in`/`.nic.in` domains.
   - **06:15 IST**: Stage 4 dual-extractor consensus (`>= 0.98`) + isolated shadow-DB golden regression suite execution (`tests/golden/`) for zero-touch auto-promotion.
   - **06:30 IST**: Stage 2 Redis rule cache refresh and Tier 4 confidence score decay.
   - **24-Hour Canary Rollback**: Monitors `engine_gap_event` spikes to autonomously revert faulty promotions within 24 hours.
5. **Security & PII Stripping**: Scans and redacts all Indian PII (PAN, Aadhaar, UAN, phone, email, and quasi-judicial party names) before indexing into vector stores.

---

## 📁 Monorepo Structure

```
epfo-intelligence-system/
├── docker-compose.yml             # PostgreSQL 16 + pgvector, Redis, MinIO, Celery, FastAPI, Review UI
├── Dockerfile.api                 # Production FastAPI container
├── Dockerfile.worker              # Celery worker / beat scheduler container
├── requirements.txt               # Locked production dependencies
├── db/
│   ├── migrations/                # Stage 1 DDL (8 tables + btree_gist + functions + seed data)
│   └── statutory_store.py         # In-memory & bitemporal store with hash-chain integrity
├── engines/
│   ├── member/                    # Stage 2: Claims eligibility, pension, preflight, legal drafter
│   ├── employer/                  # Stage 2: Coverage, 50% add-back, ECR batch validator, penalties
│   └── common.py                  # MemberCaseInput, EmployerCaseInput, EngineResult
├── ingest/
│   ├── celery_app.py              # Autonomous 06:00 -> 06:15 -> 06:30 IST schedule clock
│   └── workers/                   # PII redactor, security quarantine, 304 probe, diff extractor
├── gate/
│   ├── consensus_evaluator.py     # Dual-extractor consensus scorer (>= 0.98 threshold)
│   ├── shadow_db_runner.py        # Shadow-DB golden regression runner & auto-promoter
│   └── canary_rollback.py         # 24h canary monitoring, anomaly detection, autonomous rollback
├── review_ui/
│   ├── Dockerfile                 # Review UI container (Port 3000)
│   └── app.py                     # Exception-only review dashboard for <10% escalations
├── api/
│   ├── main.py                    # FastAPI gateway (/health, /metrics, CORS)
│   ├── auth.py                    # Tenant API-key & JWT bearer authentication
│   ├── citation_verifier.py       # Post-generation SHA-256 citation-lock verifier
│   ├── rag_engine.py              # Precedents store & Tier 4 troubleshooting KB
│   └── v1/
│       ├── schemas.py             # Pydantic request/response schemas
│       └── endpoints.py           # Production compliance endpoints
└── tests/
    ├── stage1/                    # Boundary date & SQL schema tests (22 tests)
    ├── golden/                    # Stage 2 Authoritative Golden Scenarios (MEM/EMP/GAP) (7 tests)
    ├── ingest/                    # Stage 3 Ingestion & PII pipeline tests (10 tests)
    ├── gate/                      # Stage 4 Consensus, shadow DB, canary rollback (9 tests)
    └── api/                       # Stage 5 FastAPI, ECR validator, legal drafter (17 tests)
```

---

## 🚀 Quickstart & Local Execution

### 1. Run Automated Test Matrix (65 Tests)
```powershell
cd C:\Users\acer\Documents\GitHub\epfo-intelligence-system
python -m pytest tests/ -v
```

### 2. Launch Local FastAPI Server
```powershell
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation is live at: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 3. Containerized Full Stack Deployment
```bash
docker compose up -d
```
Services started:
- `epfo_postgres`: PostgreSQL 16 with `pgvector` & `btree_gist` (`5432`)
- `epfo_redis`: Redis 7 (`6379`)
- `epfo_minio`: S3 Document Archive (`9000` & Console `9001`)
- `epfo_api`: FastAPI Application (`8000`)
- `epfo_worker`: Celery Ingestion Worker
- `epfo_beat`: Celery Beat Autonomous Clock (06:00/06:15/06:30 IST)
- `epfo_review_ui`: Exception Review UI (`3000`)

---

## 📡 Production API Endpoints (`/v1`)

| Endpoint | Method | Description |
|---|---|---|
| `/v1/member/evaluate` | `POST` | Member claim preflight blockers, 5th-of-month rule, eligibility & approval routing tier (`SSA` → `AO` → `APFC` → `OIC`). |
| `/v1/employer/evaluate` | `POST` | Section 1(3)(b) coverage, 50% allowance cap add-back, 12% 7Q simple interest, 14B damages, 25% Sec 7O pre-deposit. |
| `/v1/employer/ecr/validate-file` | `POST` | Stream validator for official `#~#` ECR batch text files checking wage ceiling, 12% EE math, and NCP days. |
| `/v1/portal/troubleshoot` | `POST` | Ranked Tier 4 portal workarounds with automatic `EngineGapEvent` emission on unknown errors. |
| `/v1/cases/precedents` | `POST` | Hybrid BM25/vector search over quasi-judicial & court orders with strict SHA-256 citation locking. |
| `/v1/rules/as-of` | `GET` | Point-in-time statutory parameter lookup with judicial override interception and citation envelope. |
| `/v1/legal/draft/epfigms` | `POST` | Generates formal, citation-locked EPFiGMS grievance petitions for delayed or unreasoned claim rejections. |
| `/v1/legal/draft/cgit-appeal` | `POST` | Generates Section 7-I appeal memorandum for CGIT with exact 25% Section 7O statutory pre-deposit compliance. |
| `/v1/feedback/flag` | `POST` | Submits field officer or user discrepancy tickets directly into Stage 3's verification crawler. |

---

## 📜 License & Compliance Notice
Authoritative compliance engine developed under the Indian Statutory Framework:
- *Employees' Provident Funds and Miscellaneous Provisions Act, 1952*
- *Employees' Provident Funds Scheme, 1952*
- *Employees' Pension Scheme, 1995*
- *Employees' Deposit-Linked Insurance Scheme, 1976*
- *Code on Social Security, 2020*
