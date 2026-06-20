"""Pipeline B — Semi-structured extraction.

Handles quotes with mixed layouts: partial tables, inconsistent columns,
prose mixed with pricing.  Single broad pass over the document.
"""

from __future__ import annotations

import structlog

from contracts.envelope import Envelope
from contracts.errors import ExtractionError
from contracts.extraction import ExtractionResult
from core.config import get_config
from core.llm import call_llm
from harness.document_preparer import build_user_content
from pipelines.parsing import (
    compute_confidence,
    extract_json,
    parse_header,
    parse_line_items,
    parse_totals,
)

logger = structlog.get_logger()

_BASE_CONFIDENCE = 0.75


async def run(envelope: Envelope) -> ExtractionResult:
    """Execute Pipeline B extraction on a semi-structured quote."""
    config = get_config()
    content = build_user_content(envelope)

    response = await call_llm(
        system=_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": content}],
        model=config.extraction_model,
        envelope=envelope,
        agent_name="pipeline_b_extractor",
    )

    parsed = extract_json(response)
    data = parsed if isinstance(parsed, dict) else {}

    header = parse_header(data.get("header"))
    line_items = parse_line_items(data.get("line_items"))
    totals = parse_totals(data.get("totals"))

    if not line_items:
        raise ExtractionError(
            "No line items could be extracted from the document",
            context={"pipeline": "b", "envelope_id": envelope.id},
        )

    return ExtractionResult(
        header=header,
        line_items=line_items,
        totals=totals,
        source_pipeline="b",
        raw_text=content[:1000] if isinstance(content, str) else None,
        extraction_confidence=compute_confidence(line_items, _BASE_CONFIDENCE),
    )


_EXTRACTION_PROMPT = """You are extracting data from a semi-structured supplier quote.
The document has some tabular elements but is not a clean table.

Return a single JSON object with three keys:
1. "header": {supplier_name, quote_number, quote_date, expiration_date, customer_name, customer_address, sales_rep, payment_terms, delivery_terms}
2. "line_items": [{sku, description, quantity, unit, unit_price, extended_price, confidence}, ...]
3. "totals": {subtotal, tax_amount, tax_rate, shipping, discount_amount, total}

Use null for missing fields. Use decimal numbers for all monetary values.
Return ONLY valid JSON, no other text."""
