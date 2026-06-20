"""Pipeline A — Structured table extraction.

Handles quotes with clean tabular layouts: clear columns, headers,
well-aligned rows.  This is the fastest and most accurate pipeline.

Flow: header_extractor → line_item_extractor → totals_extractor → assemble
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

_BASE_CONFIDENCE = 0.9


async def run(envelope: Envelope) -> ExtractionResult:
    """Execute Pipeline A extraction on a structured-table quote."""
    config = get_config()
    content = build_user_content(envelope)

    async def _ask(system: str, agent: str) -> str:
        return await call_llm(
            system=system,
            messages=[{"role": "user", "content": content}],
            model=config.extraction_model,
            envelope=envelope,
            agent_name=agent,
        )

    header = parse_header(extract_json(await _ask(_HEADER_PROMPT, "header_extractor")))
    line_items = parse_line_items(
        extract_json(await _ask(_LINE_ITEMS_PROMPT, "line_item_extractor"))
    )
    totals = parse_totals(extract_json(await _ask(_TOTALS_PROMPT, "totals_extractor")))

    if not line_items:
        raise ExtractionError(
            "No line items could be extracted from the document",
            context={"pipeline": "a", "envelope_id": envelope.id},
        )

    return ExtractionResult(
        header=header,
        line_items=line_items,
        totals=totals,
        source_pipeline="a",
        raw_text=content[:1000] if isinstance(content, str) else None,
        extraction_confidence=compute_confidence(line_items, _BASE_CONFIDENCE),
    )


_HEADER_PROMPT = """Extract supplier and quote header metadata from this structured table document.
Return a JSON object with fields: supplier_name, quote_number, quote_date,
expiration_date, customer_name, customer_address, sales_rep, payment_terms, delivery_terms.
Use null for fields not found. Return ONLY valid JSON."""

_LINE_ITEMS_PROMPT = """Extract all line items from this structured table document.
Return a JSON array where each item has: sku, description, quantity, unit, unit_price, extended_price, confidence.
Use decimal numbers for prices. Return ONLY valid JSON."""

_TOTALS_PROMPT = """Extract the totals section from this structured table document.
Return a JSON object with: subtotal, tax_amount, tax_rate, shipping, discount_amount, total.
Use null for fields not found. Return ONLY valid JSON."""
