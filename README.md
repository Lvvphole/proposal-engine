<div align="center">

# Proposal Engine

**Turn supplier quotes into a _customer-ready proposal_** — extracted line items,
contractor **markup** and tax applied, **payment terms** attached, the math
verified to the cent, and **nothing sent without human approval**.

![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![tests](https://img.shields.io/badge/tests-181_passing-success)
![evals](https://img.shields.io/badge/eval--gate-4_suites%20%E2%9C%93-blue)
![mypy](https://img.shields.io/badge/mypy-strict-blue)
![ruff](https://img.shields.io/badge/lint-ruff-261230)
![license](https://img.shields.io/badge/license-Proprietary-red)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6)
![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E)
![Anthropic](https://img.shields.io/badge/LLM-Claude-D97757)

</div>

> **The system never invents prices.** Extraction is validated row-by-row, money
> math is `Decimal` and cent-exact ([ADR-002](./docs/adr/002-money-decimal.md)),
> per-user tenancy isolates every quote and contractor, recovery is bounded and
> failures are **terminal** (no envelope ever strands mid-pipeline), and every
> customer-facing proposal requires a contractor's explicit approval before
> delivery.

## Overview

Residential contractors get supplier quotes in dozens of formats — PDFs,
emailed tables, photographed price sheets. Turning those into customer-facing
proposals is manual, slow, and error-prone; the 7–45 day window between quote
receipt and proposal delivery is where deals die.

Proposal Engine ingests any quote format, classifies it, runs the right
extraction pipeline, validates the result against typed contracts, applies the
contractor's **default + per-category markup** plus tax, renders a printable
customer document, and surfaces it for human approval — end-to-end.

```
Supplier quote (PDF · image · email · table)
        │
        ▼
  Classifier ──► Pipeline A / B / C  (structured · semi · unstructured)
        │              │
        │              ▼
        │        Validation Gate ──► row-by-row pricing (Decimal, cents)
        │                                  │
        │                                  ▼
        │                          Review Surface (human-in-the-loop)
        │                                  │
        │                                  ▼
        └──── Recovery loop ───►   Customer-ready Proposal (HTML, print/PDF)
              (bounded retry,
               terminal failures)
```

## What's in the box

| Capability | Where | Notes |
|---|---|---|
| Multi-pipeline extraction (A/B/C) | `pipelines/pipeline_a..c/` | LLM-routed by `pipelines/classifier.py` |
| Robust JSON recovery | `pipelines/parsing.py` | Fenced / prose-wrapped output, per-row validation |
| Contract-enforced validation gate | `pipelines/validation_gate.py` | Subtotal tolerance, confidence threshold |
| Pricing — markup, tax, terms | `pipelines/proposal_builder.py` | Pure, deterministic, cent-rounded (ADR-002) |
| HTML proposal renderer | `pipelines/proposal_renderer.py` | Print-to-PDF; supplier cost / margin hidden |
| Contractor preference engine | `rag/contractor_context.py`, REST + MCP | DB-backed, per-user |
| Auth + per-user tenancy | `app/api/auth.py` | Supabase JWT, owner-scoped reads/writes |
| Recovery loop | `pipelines/orchestrator.py::_extract_with_recovery` | Pipeline C fallback; terminal `FAILED` state |
| Eval gate (deterministic) | `eval/run_evals.py`, `eval/goldens/*.jsonl` | 4 suites at 100% — guards extraction + parsing + classification + pricing |
| Review Surface | `frontend/components/ReviewSurface.tsx` | Live extraction, marked-up proposal, approve/reject |
| MCP server | `proposal_engine_mcp/` | Local stdio for Claude Desktop / Claude Code |

## Stack

- **Backend** — FastAPI + uvicorn, SQLAlchemy async, Anthropic SDK, Alembic migrations
- **Frontend** — Next.js 14 (App Router) + Tailwind, `@supabase/supabase-js`
- **Database** — Supabase Postgres (asyncpg + TLS; pooler-aware URL normalization)
- **Auth** — Supabase JWT (HS256, audience-checked); per-user tenancy via `owner_id`
- **CI gates** — `ruff` (lint+format), `mypy --strict`, `pytest` (181), `eval/run_evals.py` (4 suites)
- **Hosting** — Render (recommended) **or** AWS ECS Fargate · Vercel (frontend) · Supabase (DB)

## Quick start (local)

```bash
# Backend
pip install -e ".[dev]"
cp infra/.env.example .env        # set ANTHROPIC_API_KEY; DATABASE_URL defaults to sqlite
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
cp .env.example .env.local        # API_PROXY_TARGET defaults to http://localhost:8000
npm install
npm run dev

# MCP (optional, for Claude Desktop / Claude Code)
python -m proposal_engine_mcp
```

Then open <http://localhost:3000>, upload a supplier quote, and the full
extract → price → review → deliver loop runs locally.

## Deploy

Pick **one** backend host; the frontend always goes on Vercel, the DB on
Supabase. Same Docker image either way — re-platforming later is just changing
the target.

| Path | Backend host | Setup | When |
|---|---|---|---|
| **Render** _(recommended)_ | Render web service | Connect repo · paste 3 secrets · deploy — ~10 min | Pilot / first production deploy |
| **AWS ECS** | ECS Fargate + ALB | Terraform `apply` · GitHub OIDC role · `deploy.yml` | Need VPC / IAM control |

→ Render runbook: **[`docs/RENDER_DEPLOY.md`](./docs/RENDER_DEPLOY.md)**
→ AWS bootstrap: **[`docs/AWS_SETUP.md`](./docs/AWS_SETUP.md)**

> **Vercel root directory must be set to `frontend/`** — otherwise the deploy
> returns Next.js's own 404 because Vercel builds from the repo root.

## Repository layout

| Path | What's there |
|---|---|
| `app/` | FastAPI app: REST routes, SSE events, auth dependency |
| `contracts/` | Typed contracts (extraction, classifier, contractor, proposal, review, errors) |
| `pipelines/` | Orchestrator, classifier, A/B/C pipelines, parsing, validation gate, proposal builder + renderer |
| `harness/` | Budget, retry, escalation, hooks, observability, tracing, ORM models |
| `core/` | Async DB engine (Supabase asyncpg/TLS), LLM client, message bus, streaming |
| `rag/` | Contractor preferences, supplier catalog, few-shot selector |
| `frontend/` | Next.js Review Surface + Supabase Auth gate |
| `eval/` | Deterministic scorers, golden datasets (`*_v1.jsonl`), baseline |
| `migrations/` | Alembic schema (envelopes, contractors, owner_id) |
| `proposal_engine_mcp/` | MCP server (stdio) + tool handlers |
| `infra/` | `Dockerfile`, `docker-compose.yml`, Terraform (`ecr`, `alb`, `ecs`, `github_oidc`) |
| `docs/` + `docs/adr/` | Architecture, deployment, evals, ADRs |

## Development

```bash
ruff check . && ruff format --check .          # lint + format
python -m mypy contracts/ core/ harness/ pipelines/   # strict types
pytest -q                                       # 181 tests
python eval/run_evals.py                        # 4 deterministic suites
```

All four gate the merge: CI workflows in `.github/workflows/{ci,eval-gate,regression-gate}.yml`.

## Documentation

- [Architecture overview](./CLAUDE.md)
- [Extraction architecture](./docs/EXTRACTION_ARCHITECTURE.md)
- [Deployment overview](./docs/DEPLOYMENT.md) — three pieces (Supabase + Vercel + backend)
- [Render deploy](./docs/RENDER_DEPLOY.md) — simplest backend path
- [AWS setup](./docs/AWS_SETUP.md) — first-time AWS bootstrap for the ECS path
- [Evaluation methodology](./docs/EVALS.md)
- [Directory structure](./docs/DIRECTORY_STRUCTURE.md)
- ADRs: [orchestration](./docs/adr/001-orchestration-architecture.md) · [money/Decimal](./docs/adr/002-money-decimal.md) · [token economics](./docs/adr/003-token-economics.md) · [SaaS positioning](./docs/adr/004-saas-positioning.md)

## License

Proprietary. All rights reserved.
