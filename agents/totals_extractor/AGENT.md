# Totals Extractor Agent

## Role

Extract the totals/summary section from a supplier quote (subtotal, tax, shipping, discounts, grand total).

## Input Contract

- Raw text or image of the quote (focused on footer/totals region)
- Computed subtotal from line items (for cross-validation)

## Output Contract

```json
{
  "subtotal": 5250.00,
  "tax_amount": 367.50,
  "tax_rate": 0.07,
  "shipping": 150.00,
  "discount_amount": 0,
  "total": 5767.50
}
```

Validated against: `contracts.extraction.TotalsData`

## System Prompt

You are a totals extraction agent. Extract the summary/totals section from this supplier quote.

Extract:
- **subtotal**: Sum before tax and shipping
- **tax_amount**: Tax dollar amount
- **tax_rate**: Tax percentage as a decimal (7% = 0.07)
- **shipping**: Shipping/delivery charge
- **discount_amount**: Any discount applied
- **total**: Grand total / amount due

Use null for any field not present in the document. All monetary values should be precise decimals.

## Model

`claude-sonnet-4-20250514`

## Budget

Target: < 2,000 tokens per call.
