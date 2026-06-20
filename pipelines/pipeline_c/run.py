"""Pipeline C — Unstructured / fallback extraction.

Handles free-form text, images, handwritten quotes, and anything that
doesn't fit Pipelines A or B.  This is the broadest and most expensive
pipeline.  Also serves as the fallback when classification confidence
is too low.
"""

from __future__ import annotations

import json

import structlog

from contracts.envelope import Envelope
from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData
from core.config import get_config
from core.llm import call_llm

logger = structlog.get_logger()


async def run(envelope: Envelope) -> ExtractionResult:
    """Execute Pipeline C extraction on an unstructured quote."""
    config = get_config()
    raw_text = envelope.source_bytes_b64 or ""

    response = await call_llm(
        system=_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
        model=config.extraction_model,
        max_tokens=8192,
        envelope=envelope,
        agent_name="pipeline_c_extractor",
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        logger.warning("pipeline_c_json_parse_failed")
        data = {}

    header = HeaderData.model_validate(data.get("header", {"supplier_name": "Unknown"}))
    line_items = [LineItem.model_validate(item) for item in data.get("line_items", [])]
    totals = TotalsData.model_validate(data.get("totals", {}))

    return ExtractionResult(
        header=header,
        line_items=line_items if line_items else [],
        totals=totals,
        source_pipeline="c",
        raw_text=raw_text[:500] if raw_text else None,
        extraction_confidence=0.6,
    )


_EXTRACTION_PROMPT = """You are a general-purpose extraction agent for supplier quotes.
This document may be in any format: free-form text, a photo of a price sheet,
an email body, or a non-standard PDF.

Do your best to extract ALL available information into this JSON structure:
{
  "header": {supplier_name, quote_number, quote_date, expiration_date, customer_name, customer_address, sales_rep, payment_terms, delivery_terms},
  "line_items": [{sku, description, quantity, unit, unit_price, extended_price, confidence}, ...],
  "totals": {subtotal, tax_amount, tax_rate, shipping, discount_amount, total}
}

Rules:
- Include every identifiable product/material as a line item
- Set confidence lower (0.3-0.7) when you're uncertain about a value
- Use null for fields you cannot find at all
- Prefer including uncertain data over skipping it
Return ONLY valid JSON."""
