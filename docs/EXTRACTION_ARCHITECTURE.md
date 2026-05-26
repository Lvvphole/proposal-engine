# Extraction Architecture

## Overview

The extraction system converts unstructured supplier quotes (PDFs, emails, images) into structured `ExtractionResult` objects containing header data, line items, and totals. Every boundary between components is enforced by typed contracts.

## Data Flow

```
Input Document
      │
      ▼
┌─────────────┐
│  Classifier  │  Model: Haiku  │  Budget: <2K tokens
│  (AGENT.md)  │  Output: QuoteFormat + pipeline routing
└──────┬──────┘
       │
       ├── confidence ≥ 0.7 ──► Route to Pipeline A, B, or C
       └── confidence < 0.7 ──► Fallback to Pipeline C
       │
       ▼
┌──────────────────────────────────────────────┐
│  Pipeline A (structured)                      │
│  ┌──────────┐  ┌────────────┐  ┌───────────┐ │
│  │ Header   │→ │ Line Items │→ │  Totals   │ │
│  │ Extractor│  │ Extractor  │  │ Extractor │ │
│  └──────────┘  └────────────┘  └───────────┘ │
│  3 steps, handoff validation between each     │
│  Target confidence: 0.9                       │
├──────────────────────────────────────────────┤
│  Pipeline B (semi-structured)                 │
│  Single-pass extraction with structured output│
│  Target confidence: 0.75                      │
├──────────────────────────────────────────────┤
│  Pipeline C (unstructured / fallback)         │
│  Single-pass, max tokens 8192                 │
│  Target confidence: 0.6                       │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────┐
│ Validation Gate   │  5 checks:
│                   │  1. Items exist
│                   │  2. Required fields present
│                   │  3. Subtotal consistency (2% tolerance)
│                   │  4. No negative prices
│                   │  5. Confidence threshold met
└────────┬─────────┘
         │
         ├── PASS ──► Review Surface (human approval)
         │
         └── FAIL ──► Recovery Agent (max 2 retries)
                          │
                          ├── Recovers ──► Back to Validation Gate
                          └── Exhausted ──► Escalation → Human Review
```

## Contract Enforcement

Every agent boundary uses `harness/handoff.py` to validate data shape:

1. Agent produces raw output (JSON from LLM)
2. `handoff.validate()` parses into the target contract type (e.g., `LineItem`)
3. Validation failure triggers `ContractViolation` error
4. Orchestrator catches violation and routes to recovery or escalation

This ensures malformed data never silently propagates downstream.

## Budget Tracking

Each envelope has a $2.00 cost ceiling. The budget tracker in `harness/budget.py` records token usage per agent call and computes cost using model-specific rates from `policies/budget_policy.json`. If the envelope budget is exhausted mid-extraction, the orchestrator halts and escalates to human review — it never retries on budget errors.

A daily limit of $25.00 prevents runaway costs across all envelopes.

## Pipeline Selection Logic

The classifier routes documents based on detected format:

| Format | Pipeline | Characteristics |
|---|---|---|
| `structured_table` | A | Clear column headers, consistent delimiters, SKU codes |
| `semi_structured` | B | Email quotes, partial tables, prose with embedded prices |
| `unstructured` | C | Handwritten notes, verbal transcriptions, images |

When the classifier's confidence is below 0.7, the document routes to Pipeline C regardless of detected format. When a supplier has a known preferred pipeline in the catalog (`rag/supplier_catalog.py`), that preference is used as a tiebreaker.

## Recovery Agent

The recovery agent receives the failed extraction, the validation errors, and the original document. It makes up to 2 targeted attempts to fix specific issues (e.g., re-extracting a missed line item, correcting a subtotal). Each retry is a fresh LLM call with the error context injected into the prompt.

Recovery never retries budget errors or contract violations at the type level — those indicate structural problems that require human attention.

## Quality Scoring

`harness/quality_judge.py` produces a 4-factor score (0.0–1.0):

1. **Completeness** — are all expected fields populated?
2. **Consistency** — do computed totals match stated totals?
3. **Confidence** — average extraction confidence across items
4. **Plausibility** — are quantities and prices in reasonable ranges?

Extractions scoring below 0.75 are automatically flagged for human review per `policies/human_review_policy.json`.
