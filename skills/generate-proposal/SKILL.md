# Skill: Generate Proposal

## Purpose

Transform a validated `ExtractionResult` into a contractor-ready proposal with markup, branding, and payment terms applied.

## Trigger

User asks to generate a proposal from an existing extraction, or this skill runs automatically after a successful extraction + human approval.

## Workflow

1. **Load extraction.** Retrieve the approved `ExtractionResult` by envelope ID.

2. **Load contractor context.** Call `rag/contractor_context.py::get_context()` to retrieve:
   - Markup rules (default percentage, category-specific overrides)
   - Payment terms
   - Branding (logo path, company name, license number, contact info)

3. **Apply markup.** For each line item:
   - Look up category-specific markup; fall back to default percentage
   - Compute contractor price: `extended_price * (1 + markup_pct)`
   - Accumulate new subtotal

4. **Compute proposal totals.** New subtotal from marked-up items, apply tax rate from original extraction (if present), compute final total.

5. **Format proposal.** Generate a professional proposal document with:
   - Contractor's header/branding
   - Customer information (from extraction header)
   - Line item table with contractor prices (supplier prices hidden)
   - Totals section
   - Payment terms
   - Validity period (default: 30 days)

6. **Present for review.** Display the formatted proposal to the user. This is the final human checkpoint before delivery.

## Output

- Formatted proposal (Markdown or PDF)
- Proposal summary with margin analysis

## Contracts

- Input: `ExtractionResult` + `contractor_id`
- Output: Formatted proposal document
- Never auto-sends to the customer — human approval is mandatory
