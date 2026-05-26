# ADR-002: Use Decimal for All Monetary Values

**Status:** Accepted
**Date:** 2024-06-01
**Author:** Emory

## Context

Supplier quotes contain monetary values (unit prices, extended prices, subtotals, tax amounts, totals) that must be extracted and computed accurately. Floating-point arithmetic introduces rounding errors that accumulate across line items.

## Decision

All monetary fields in the contracts layer use Python's `decimal.Decimal` type. The `LineItem`, `TotalsData`, and `ExtractionResult` contracts enforce this at the type level via Pydantic validators.

## Rationale

- `0.1 + 0.2 == 0.30000000000000004` in float arithmetic. For a contractor sending a $50,000 proposal to a customer, a one-cent rounding error looks unprofessional; a larger error could create legal liability.
- Decimal arithmetic matches how the source documents represent money (fixed-point notation).
- Pydantic v2 natively supports Decimal serialization and validation.

## Implementation

- `LineItem.unit_price`, `LineItem.extended_price`: `Decimal`
- `TotalsData.subtotal`, `TotalsData.tax_amount`, `TotalsData.total`: `Decimal | None`
- LLM outputs are strings; `handoff.validate()` converts to Decimal during contract enforcement
- JSON serialization uses string representation to avoid float conversion

## Consequences

- Slightly more verbose than float in test fixtures
- LLM responses must be parsed carefully — the handoff layer strips currency symbols and commas before Decimal conversion
- Comparison in validation gate uses a 2% tolerance to account for LLM extraction imprecision, not arithmetic error

## Alternatives Rejected

- **Float with rounding:** Simpler but accumulates errors on invoices with 20+ line items
- **Integer cents:** Requires division/multiplication at display boundaries; less readable in logs and debug output
