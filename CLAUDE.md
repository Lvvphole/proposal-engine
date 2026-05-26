# Proposal Engine — CLAUDE.md

## What This Is

An AI-powered system that ingests supplier quotes (PDFs, emails, images), extracts structured data, and generates contractor-ready proposals with markup, tax, and delivery terms. Built as a Services-as-Software play for residential contractors.

## Architecture Overview

```
Supplier Quote (PDF/image/email)
        │
        ▼
  ┌─────────────┐
  │  Classifier  │  ← Determines quote format + routes to pipeline
  └──────┬──────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
  [A]  [B]  [C]   ← Extraction pipelines (structured / semi / unstructured)
    └────┼────┘
         ▼
  ┌─────────────┐
  │ Validation   │  ← Contract-enforced checks (totals, line items, schema)
  │    Gate      │
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  Proposal    │  ← Applies markup, contractor prefs, generates output
  │  Builder     │
  └──────┬──────┘
         ▼
  Review Surface (human-in-the-loop)
```

## Key Commands

```bash
# Run the full test suite
pytest tests/ -v

# Run evals against golden datasets
python eval/run_evals.py

# Start the API server (dev)
uvicorn app.main:app --reload --port 8000

# Start the MCP server
python -m proposal_engine_mcp
```

## Claude Code Slash Commands

- `/check-cost` — Estimate token cost for a pipeline run
- `/new-supplier-pipeline` — Scaffold a new extraction pipeline for an unseen supplier format
- `/review-contract-change` — Validate a contracts/ change against existing tests + evals
- `/run-evals` — Execute eval suite and compare against baseline

## Contracts (Type Contracts, Not Legal)

All data flowing between agents must satisfy the type contracts in `contracts/`. These are enforced at pipeline boundaries via the `validation_gate`. Never bypass the gate — if data doesn't conform, fix the extraction, don't loosen the contract.

## Key Principles

1. **Contracts are law.** Every agent's input/output is typed. The validation gate is not optional.
2. **Evals before merge.** The `eval-gate.yml` workflow blocks PRs that regress extraction accuracy.
3. **Budget awareness.** Every LLM call is wrapped with token tracking. Check `policies/budget_policy.json` for limits.
4. **Human-in-the-loop.** Proposals are never auto-sent. The Review Surface is mandatory.
5. **File-system is source of truth.** Markdown files in this repo are authoritative. External systems (Salesforce, Sheets) are regeneratable caches.

## Project Structure

See `docs/DIRECTORY_STRUCTURE.md` for the full annotated tree.

## Development Workflow

1. Branch from `main`
2. Make changes
3. Run `pytest tests/ -v` (must pass)
4. Run `python eval/run_evals.py` (must meet baseline)
5. PR triggers `ci.yml` → `eval-gate.yml` → `regression-gate.yml`
6. Merge to `main` triggers `deploy.yml`

## Environment Variables

Copy `infra/.env.example` to `.env` at the project root. Required:

- `ANTHROPIC_API_KEY` — Claude API access
- `DATABASE_URL` — PostgreSQL connection string
- `BUDGET_DAILY_LIMIT_USD` — Hard ceiling on daily LLM spend
