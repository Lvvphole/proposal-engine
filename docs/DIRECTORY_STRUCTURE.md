# Directory Structure

Annotated map of the proposal-engine repository.

```
proposal-engine/
│
├── CLAUDE.md                        # Primary instruction file for Claude Code
├── README.md                        # Project overview and quick start
├── pyproject.toml                   # Python deps and tooling config
├── package.json                     # Frontend deps (Next.js)
│
├── contracts/                       # TYPE SYSTEM — all inter-agent data contracts
│   ├── __init__.py                  # Public API exports
│   ├── extraction.py                # LineItem, HeaderData, TotalsData, ExtractionResult
│   ├── classifier.py                # QuoteFormat, ClassificationResult
│   ├── envelope.py                  # Envelope (work unit), EnvelopeStatus
│   ├── events.py                    # DomainEvent, EventKind
│   ├── review.py                    # ReviewDecision, ReviewVerdict
│   └── errors.py                    # Error hierarchy
│
├── core/                            # INFRASTRUCTURE — shared services
│   ├── config.py                    # Pydantic settings from .env
│   ├── llm.py                       # Anthropic SDK wrapper + token tracking
│   ├── db.py                        # SQLAlchemy async engine
│   └── message_bus.py               # In-process event pub/sub
│
├── agents/                          # AGENT DEFINITIONS — one folder per agent
│   ├── classifier/AGENT.md          # Classification system prompt + contract
│   ├── header_extractor/AGENT.md    # Header extraction
│   ├── line_item_extractor/AGENT.md # Line item extraction
│   ├── totals_extractor/AGENT.md    # Totals extraction
│   ├── recovery_agent/AGENT.md      # Failed extraction recovery
│   └── pipeline_c_fallback/AGENT.md # Broad-spectrum fallback
│
├── pipelines/                       # PIPELINE IMPLEMENTATIONS
│   ├── orchestrator.py              # Central control loop (classify → extract → validate)
│   ├── classifier.py                # Routes a quote to pipeline A/B/C (LLM)
│   ├── parsing.py                   # Robust JSON extraction + per-row validation
│   ├── validation_gate.py           # Contract enforcement checks
│   ├── pipeline_a/run.py            # Structured table extraction
│   ├── pipeline_b/run.py            # Semi-structured extraction
│   └── pipeline_c/run.py            # Unstructured / fallback extraction
│
├── harness/                         # OPERATIONAL INFRASTRUCTURE
│   ├── budget.py                    # Token/cost budget enforcement
│   ├── retry.py                     # Retry orchestration
│   ├── escalation.py                # Failure routing
│   ├── handoff.py                   # Agent boundary validation
│   ├── audit.py                     # Immutable event log
│   ├── instrumentation.py           # Metrics and counters
│   ├── observability.py             # Structured logging
│   ├── quality_judge.py             # Extraction quality scoring
│   └── sandbox.py                   # Document processing isolation
│
├── memory/                          # MEMORY SYSTEM
│   ├── working_state.py             # Request-scoped state
│   ├── cache.py                     # LRU + TTL cache
│   ├── static_store.py              # Supplier catalog loader
│   ├── learned_store.py             # Human correction patterns
│   └── retrieval_store.py           # Embedding-based retrieval
│
├── rag/                             # RETRIEVAL-AUGMENTED GENERATION
│   ├── contractor_context.py        # Contractor preference loading
│   ├── embeddings.py                # Vector embedding + similarity
│   ├── few_shot_selector.py         # Few-shot example selection
│   └── supplier_catalog.py          # Supplier format registry
│
├── eval/                            # EVALUATION FRAMEWORK
│   ├── run_evals.py                 # CLI eval runner
│   ├── goldens/                     # Ground-truth test datasets
│   ├── judges/                      # Scoring functions
│   └── results/baseline.json        # Current accuracy baseline
│
├── proposal_engine_mcp/             # MCP SERVER
│   ├── __main__.py                  # Entry point
│   ├── http.py                      # Server configuration
│   ├── domain/                      # MCP domain models
│   └── handlers/                    # Tool handler implementations
│
├── app/                             # HTTP API
│   ├── main.py                      # FastAPI application
│   └── api/routes.py                # REST endpoints
│
├── frontend/                        # REVIEW SURFACE (Next.js)
│   ├── app/page.tsx                 # Main page
│   └── components/ReviewSurface.tsx # Human review component
│
├── policies/                        # POLICY CONFIGURATION (JSON)
│   ├── budget_policy.json
│   ├── model_routing_policy.json
│   ├── human_review_policy.json
│   ├── eval_gate_policy.json
│   └── ... (8 policy files total)
│
├── skills/                          # CLAUDE CODE SKILLS
│   ├── extract-supplier-quote/      # Skill for running extraction
│   ├── generate-proposal/           # Skill for proposal generation
│   ├── improve-extraction/          # Skill for accuracy improvement
│   └── onboard-contractor/          # Skill for new contractor setup
│
├── .claude/commands/                # CLAUDE CODE SLASH COMMANDS
│   ├── check-cost.md
│   ├── new-supplier-pipeline.md
│   ├── review-contract-change.md
│   └── run-evals.md
│
├── commercial/                      # COMMERCIAL PLAYBOOKS
│   ├── CONTRACTOR_DIAGNOSTIC_PLAYBOOK.md
│   ├── PILOT_AGREEMENT_TEMPLATE.md
│   └── WEEKLY_TRACKING_DASHBOARD.md
│
├── infra/                           # DEPLOYMENT
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   └── terraform/
│
├── scripts/                         # UTILITY SCRIPTS
│   ├── label_pdfs.py                # Golden dataset labeling tool
│   └── shadow_compare.py            # A/B pipeline comparison
│
├── tests/                           # TEST SUITE
│   ├── test_contracts.py
│   ├── test_validation_gate.py
│   └── test_orchestrator.py
│
├── docs/                            # DOCUMENTATION
│   ├── DIRECTORY_STRUCTURE.md       # This file
│   ├── EXTRACTION_ARCHITECTURE.md   # How extraction works
│   ├── EVALS.md                     # Eval methodology
│   └── adr/                         # Architecture Decision Records
│
└── future/                          # FUTURE CAPABILITIES
    └── lead-gen/README.md
```
