"""Robust parsing of LLM extraction output.

LLMs rarely return bare JSON — responses come wrapped in ```json fences,
prefaced with prose ("Here is the JSON:"), or with a trailing explanation.
These helpers recover the JSON payload and validate it into our contracts
*without* silently discarding everything when a single row is malformed.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog
from pydantic import ValidationError

from contracts.extraction import HeaderData, LineItem, TotalsData

logger = structlog.get_logger()

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any | None:
    """Recover a JSON value from a model response.

    Tries, in order: the trimmed text, the contents of a ```json fence, and
    the first balanced ``{...}`` / ``[...]`` region. Returns the parsed value,
    or ``None`` if nothing parses.
    """
    if not text or not text.strip():
        return None

    candidates: list[str] = [text.strip()]

    fence = _FENCE.search(text)
    if fence:
        candidates.append(fence.group(1).strip())

    balanced = _first_balanced(text)
    if balanced:
        candidates.append(balanced)

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue

    logger.warning("json_extract_failed", preview=text[:120])
    return None


def _first_balanced(text: str) -> str | None:
    """Return the first balanced JSON object/array substring, or None.

    Brace-aware and string-aware (ignores braces inside string literals).
    """
    start = next((i for i, ch in enumerate(text) if ch in "{["), None)
    if start is None:
        return None

    depth = 0
    in_string = False
    escaped = False
    for j in range(start, len(text)):
        ch = text[j]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                return text[start : j + 1]
    return None


def parse_header(raw: Any) -> HeaderData:
    """Validate header data, falling back to a minimal placeholder."""
    if isinstance(raw, dict):
        try:
            return HeaderData.model_validate(raw)
        except ValidationError as exc:
            logger.warning("header_parse_failed", error=str(exc))
    return HeaderData(supplier_name="Unknown")


def parse_line_items(raw: Any) -> list[LineItem]:
    """Validate line items one-by-one, skipping (not dropping all) bad rows."""
    if not isinstance(raw, list):
        return []

    items: list[LineItem] = []
    for index, entry in enumerate(raw):
        try:
            items.append(LineItem.model_validate(entry))
        except ValidationError as exc:
            logger.warning("line_item_skipped", index=index, error=str(exc))
    return items


def parse_totals(raw: Any) -> TotalsData:
    """Validate totals, falling back to an empty totals block."""
    if isinstance(raw, dict):
        try:
            return TotalsData.model_validate(raw)
        except ValidationError as exc:
            logger.warning("totals_parse_failed", error=str(exc))
    return TotalsData()


def compute_confidence(line_items: list[LineItem], base: float) -> float:
    """Derive an extraction confidence from the data instead of hardcoding it.

    Combines the pipeline's prior (``base``, reflecting how well-suited the
    pipeline is to the format) with the mean per-line-item confidence. An
    empty extraction is penalised heavily.
    """
    if not line_items:
        return round(base * 0.4, 3)
    mean_item = sum(item.confidence for item in line_items) / len(line_items)
    return round(0.4 * base + 0.6 * mean_item, 3)
