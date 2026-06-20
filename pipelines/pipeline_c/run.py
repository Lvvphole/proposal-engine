"""Pipeline C — Unstructured / fallback extraction.

Handles free-form text, images, handwritten quotes, and anything that
doesn't fit Pipelines A or B.  This is the broadest and most expensive
pipeline.  Also serves as the fallback when classification confidence
is too low.
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

_BASE_CONFIDENCE = 0.6


async def run(envelope: Envelope) -> ExtractionResult:
    """Execute Pipeline C extraction on an unstructured quote."""
    config = get_config()
    content = build_user_content(envelope)

    response = await call_llm(
        system=_EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": content}],
        model=config.extraction_model,
        max_tokens=8192,
        envelope=envelope,
        agent_name="pipeline_c_extractor",
    )

    parsed = extract_json(response)
    data = parsed if isinstance(parsed, dict) else {}

    header = parse_header(data.get("header"))
    line_items = parse_line_items(data.get("line_items"))
    totals = parse_totals(data.get("totals"))

    if not line_items:
        raise ExtractionError(
            "No line items could be extracted from the document",
            context={"pipeline": "c", "envelope_id": envelope.id},
        )

    return ExtractionResult(
        header=header,
        line_items=line_items,
        totals=totals,
        source_pipeline="c",
        raw_text=content[:1000] if isinstance(content, str) else None,
        extraction_confidence=compute_confidence(line_items, _BASE_CONFIDENCE),
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
