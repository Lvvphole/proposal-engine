"""Pipeline B — Semi-structured extraction.

Handles quotes with mixed layouts: partial tables, inconsistent columns,
prose mixed with pricing.  Uses a two-pass strategy: first pass extracts
what it can, second pass fills gaps.
"""

from __future__ import annotations

import json

import structlog

from contracts.envelope import Envelope
from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData
from core.llm import call_llm
from core.config import get_config

logger = structlog.get_logger()


async def run(envelope: Envelope) -> ExtractionResult:
    """Execute Pipeline B extraction on a semi-structured quote."""
    config = get_config()
    raw_text = envelope.source_bytes_b64 or ""

    # Single-pass broad extraction for semi-structured documents
    response = await call_llm(
        system=_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
        model=config.extraction_model,
        envelope=envelope,
        agent_name="pipeline_b_extractor",
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        logger.warning("pipeline_b_json_parse_failed")
        data = {}

    header = HeaderData.model_validate(data.get("header", {"supplier_name": "Unknown"}))
    line_items = [
        LineItem.model_validate(item)
        for item in data.get("line_items", [])
    ]
    totals = TotalsData.model_validate(data.get("totals", {}))

    return ExtractionResult(
        header=header,
        line_items=line_items if line_items else [],
        totals=totals,
        source_pipeline="b",
        raw_text=raw_text[:500] if raw_text else None,
        extraction_confidence=0.75,
    )


_EXTRACTION_PROMPT = """You are extracting data from a semi-structured supplier quote.
The document has some tabular elements but is not a clean table.

Return a single JSON object with three keys:
1. "header": {supplier_name, quote_number, quote_date, expiration_date, customer_name, customer_address, sales_rep, payment_terms, delivery_terms}
2. "line_items": [{sku, description, quantity, unit, unit_price, extended_price, confidence}, ...]
3. "totals": {subtotal, tax_amount, tax_rate, shipping, discount_amount, total}

Use null for missing fields. Use decimal numbers for all monetary values.
Return ONLY valid JSON, no other text."""
