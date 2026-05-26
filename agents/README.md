# Agents

Each agent is a single-responsibility AI component with a well-defined input contract and output contract.  Agents are stateless — all state lives in the Envelope that flows through them.

## Agent Inventory

| Agent | Input | Output | Model |
|---|---|---|---|
| `classifier` | Raw document bytes | `ClassificationResult` | Haiku |
| `header_extractor` | Raw text/image | `HeaderData` | Sonnet |
| `line_item_extractor` | Raw text/image | `list[LineItem]` | Sonnet |
| `totals_extractor` | Raw text/image | `TotalsData` | Sonnet |
| `recovery_agent` | Failed `ExtractionResult` + error context | Repaired `ExtractionResult` | Sonnet |
| `pipeline_c_fallback` | Raw document (any format) | `ExtractionResult` | Sonnet |

## AGENT.md Convention

Each agent folder contains an `AGENT.md` file that serves as:
1. The system prompt template for that agent's LLM calls
2. Documentation for developers
3. The contract specification (what it accepts, what it produces)

Claude Code reads these files to understand agent behavior when making changes.
