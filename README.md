# Proposal Engine

AI-powered contractor proposal generation from supplier quotes.
AI-powered quote-to-proposal automation for residential contractors.

## Problem
Proposal Engine turns supplier quotes in PDFs, emails, tables, and photographed price sheets into structured, reviewable contractor proposals. It combines multi-pipeline AI extraction, contract validation, contractor-specific preferences, and a mandatory human review workflow so teams can move from supplier quote to customer-ready proposal faster and with fewer manual errors.

Residential contractors receive supplier quotes in dozens of formats — PDFs, emailed tables, photographed price sheets. Turning these into customer-facing proposals is manual, error-prone, and slow. The 7–45 day window between quote receipt and proposal delivery is where deals die.
## What it does

## Solution
- Extracts headers, line items, totals, and qualifiers from supplier quote documents.
- Validates extracted data against shared Pydantic contracts before proposal generation.
- Applies contractor preferences such as markup rules, terms, and proposal defaults.
- Tracks token budgets, retries, policy gates, audit events, and evaluation results.
- Exposes a FastAPI backend, MCP server, and Next.js review surface.

Proposal Engine ingests any supplier quote format, extracts structured line-item data using multi-pipeline AI extraction, applies contractor-specific markup and terms, and generates a ready-to-send proposal — with mandatory human review before delivery.
## Repository layout

## Quick Start
| Path | Purpose |
| --- | --- |
| `app/` | FastAPI application and REST routes. |
| `contracts/` | Shared data contracts for extraction, review, events, and contractors. |
| `pipelines/` | Extraction pipelines, orchestration, remediation, and validation gate. |
| `harness/` | Policy, budget, observability, retry, tracing, and audit helpers. |
| `proposal_engine_mcp/` | MCP server and tool handlers for proposals, suppliers, and contractors. |
| `frontend/` | Next.js review UI for live extraction review and decisions. |
| `eval/` | Golden datasets, judges, baseline results, and eval runner. |
| `infra/` | Docker, Compose, and Terraform deployment assets. |
| `docs/` | Architecture, deployment, eval, and ADR documentation. |

## Quick start

```bash
# Backend
pip install -e ".[dev]"
cp infra/.env.example .env
# Edit .env with your keys
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
cd frontend
npm install
npm run dev

# MCP Server
# MCP server
python -m proposal_engine_mcp
```

## Architecture
## Development checks

See [CLAUDE.md](./CLAUDE.md) for the full architecture overview and development workflow.
```bash
pytest
ruff check .
mypy .
cd frontend && npm run lint && npm run typecheck
```

## Status

- ✅ Multi-pipeline extraction (Pipelines A, B, C)
- ✅ Contract-enforced validation gate
- ✅ Token budget tracking and policy enforcement
- ✅ Eval framework with golden datasets
- ✅ MCP server for Claude Desktop / Claude Code integration
- ✅ Review Surface (Next.js, fetches live extraction + submits decisions)
- ✅ Contractor preference engine (DB-backed, REST + MCP CRUD)
- ✅ Database schema via Alembic migrations (Supabase Postgres)
- 🔄 Deployment: frontend on Vercel, backend on AWS ECS — see
  [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) (ECS service/ALB Terraform still
  to be added)
- Multi-pipeline extraction with contract-enforced validation.
- Contractor preference management through REST and MCP interfaces.
- Review Surface for human approval before proposal delivery.
- Evaluation framework with golden datasets and quality judges.
- Deployment assets for Vercel frontend and AWS ECS backend.

## Documentation

- [Architecture overview](./CLAUDE.md)
- [Extraction architecture](./docs/EXTRACTION_ARCHITECTURE.md)
- [Deployment (overview)](./docs/DEPLOYMENT.md) — Supabase + Vercel + backend host
- [Render deploy (recommended)](./docs/RENDER_DEPLOY.md) — simplest backend host
- [AWS setup](./docs/AWS_SETUP.md) — first-time AWS bootstrap for the ECS path
- [Evaluation guide](./docs/EVALS.md)
- [Directory structure](./docs/DIRECTORY_STRUCTURE.md)

## License

Proprietary. All rights reserved.
