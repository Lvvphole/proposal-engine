"""Pipeline A — Structured table extraction.

Handles quotes with clean tabular layouts: clear columns, headers,
well-aligned rows.  This is the fastest and most accurate pipeline.

Flow: header_extractor → line_item_extractor → totals_extractor → assemble
"""

from __future__ import annotations

from typing import Any

import structlog

from contracts.envelope import Envelope
from contracts.extraction import ExtractionResult, HeaderData, LineItem, TotalsData
from core.config import get_config
from core.llm import call_llm
from harness.handoff import validate_handoff

logger = structlog.get_logger()


async def run(envelope: Envelope) -> ExtractionResult:
    """Execute Pipeline A extraction on a structured-table quote."""
    config = get_config()
    raw_text = envelope.source_bytes_b64 or ""

    # Step 1: Extract header
    header_response = await call_llm(
        system=_HEADER_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
        model=config.extraction_model,
        envelope=envelope,
        agent_name="header_extractor",
    )
    header = validate_handoff(
        _parse_header(header_response),
        HeaderData,
        source_agent="header_extractor",
        target_agent="line_item_extractor",
    )

    # Step 2: Extract line items
    items_response = await call_llm(
        system=_LINE_ITEMS_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
        model=config.extraction_model,
        envelope=envelope,
        agent_name="line_item_extractor",
    )
    line_items = _parse_line_items(items_response)

    # Step 3: Extract totals
    totals_response = await call_llm(
        system=_TOTALS_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
        model=config.extraction_model,
        envelope=envelope,
        agent_name="totals_extractor",
    )
    totals = validate_handoff(
        _parse_totals(totals_response),
        TotalsData,
        source_agent="totals_extractor",
        target_agent="assembler",
    )

    # Assemble final result
    return ExtractionResult(
        header=header,
        line_items=line_items,
        totals=totals,
        source_pipeline="a",
        raw_text=raw_text[:500] if raw_text else None,
        extraction_confidence=0.9,
    )


def _parse_header(response: str) -> dict[str, Any]:
    """Parse LLM header response into a dict.  Stub for JSON parsing."""
    import json

    try:
        parsed: dict[str, Any] = json.loads(response)
        return parsed
    except json.JSONDecodeError:
        return {"supplier_name": "Unknown"}


def _parse_line_items(response: str) -> list[LineItem]:
    """Parse LLM line items response.  Stub for JSON parsing."""
    import json

    try:
        items = json.loads(response)
        return [LineItem.model_validate(item) for item in items]
    except (json.JSONDecodeError, Exception):
        return []


def _parse_totals(response: str) -> dict[str, Any]:
    """Parse LLM totals response.  Stub for JSON parsing."""
    import json

    try:
        parsed: dict[str, Any] = json.loads(response)
        return parsed
    except json.JSONDecodeError:
        return {}


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
