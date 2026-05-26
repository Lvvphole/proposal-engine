# Proposal Engine

AI-powered contractor proposal generation from supplier quotes.

## Problem

Residential contractors receive supplier quotes in dozens of formats — PDFs, emailed tables, photographed price sheets. Turning these into customer-facing proposals is manual, error-prone, and slow. The 7–45 day window between quote receipt and proposal delivery is where deals die.

## Solution

Proposal Engine ingests any supplier quote format, extracts structured line-item data using multi-pipeline AI extraction, applies contractor-specific markup and terms, and generates a ready-to-send proposal — with mandatory human review before delivery.

## Quick Start

```bash
# Backend
pip install -e ".[dev]"
cp infra/.env.example .env
# Edit .env with your keys
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# MCP Server
python -m proposal_engine_mcp
```

## Architecture

See [CLAUDE.md](./CLAUDE.md) for the full architecture overview and development workflow.

## Status

- ✅ Multi-pipeline extraction (Pipelines A, B, C)
- ✅ Contract-enforced validation gate
- ✅ Token budget tracking and policy enforcement
- ✅ Eval framework with golden datasets
- ✅ MCP server for Claude Desktop / Claude Code integration
- 🔄 Review Surface (frontend, in progress)
- 🔄 Contractor preference engine
- 📋 Deployment automation

## License

Proprietary. All rights reserved.
