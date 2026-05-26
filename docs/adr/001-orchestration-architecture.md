# ADR-001: Orchestration Architecture

**Status:** Accepted
**Date:** 2024-06-01
**Author:** Emory

## Context

The proposal engine needs to coordinate multiple LLM calls (classification, header extraction, line item extraction, totals extraction) with validation, retry, budget enforcement, and human review. Two primary patterns were considered:

1. **Agent mesh** — agents communicate peer-to-peer via message passing
2. **Central orchestrator** — a single control loop dispatches to agents sequentially

## Decision

We chose a **central orchestrator** pattern (`pipelines/orchestrator.py`) where a single function owns the full lifecycle of an envelope from receipt through review.

## Rationale

- **Debuggability:** A linear control flow is easier to trace than distributed agent communication. Every envelope's path through the system is a single function call with clear branching.
- **Budget enforcement:** Centralized control makes it straightforward to check budget before every LLM call and halt immediately on exhaustion.
- **Contract validation:** The orchestrator calls `handoff.validate()` between every agent boundary. In a mesh, each agent pair would need its own validation logic.
- **Simplicity:** For the current scale (single-document extraction), the overhead of a distributed agent mesh provides no benefit. The orchestrator processes one envelope at a time.

## Consequences

- Adding a new pipeline requires modifying the orchestrator's routing logic
- The orchestrator is a natural bottleneck if we need parallel extraction (future consideration)
- All failure handling is centralized, which simplifies the retry/escalation code but makes the orchestrator function long

## Alternatives Rejected

- **LangGraph / state machine:** Adds framework dependency and complexity for a linear flow
- **Event-driven saga:** Appropriate at higher scale but premature for current throughput
- **Single monolithic LLM call:** No cost control, no granular retry, poor accuracy on complex documents
