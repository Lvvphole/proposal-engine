# Proposal Engine Directory Structure

```text
proposal-engine/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── eval-gate.yml
│       ├── regression-gate.yml
│       └── deploy.yml
├── .claude/
│   └── commands/
│       ├── check-cost.md
│       ├── new-supplier-pipeline.md
│       ├── review-contract-change.md
│       └── run-evals.md
├── agents/
│   ├── classifier/AGENT.md
│   ├── header_extractor/AGENT.md
│   ├── line_item_extractor/AGENT.md
│   ├── pipeline_c_fallback/AGENT.md
│   ├── recovery_agent/AGENT.md
│   ├── totals_extractor/AGENT.md
│   └── README.md
├── app/
│   ├── api/routes.py
│   └── main.py
├── commercial/
├── contracts/
├── core/
├── docs/
├── eval/
├── frontend/
├── future/
├── harness/
├── infra/
├── memory/
├── policies/
├── pipelines/
├── proposal_engine_mcp/
├── rag/
├── scripts/
├── skills/
├── tests/
├── CLAUDE.md
├── README.md
└── pyproject.toml
```

## Architecture

- Multi-agent orchestration
- MCP server integration
- Eval harness
- Human-in-the-loop escalation
- Langfuse/OpenTelemetry observability
- Postgres + pgvector memory architecture
- Docker + AWS ECS/Fargate deployment target
