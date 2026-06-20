"""Tests for robust LLM-output parsing (pipelines/parsing.py)."""

from __future__ import annotations

from decimal import Decimal

from contracts.extraction import LineItem
from pipelines.parsing import (
    compute_confidence,
    extract_json,
    parse_header,
    parse_line_items,
    parse_totals,
)


class TestExtractJson:
    def test_bare_object(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_json_fence(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_bare_fence(self):
        assert extract_json("```\n[1, 2, 3]\n```") == [1, 2, 3]

    def test_prose_wrapped(self):
        text = 'Here is the JSON you asked for:\n```json\n{"ok": true}\n```\nHope that helps!'
        assert extract_json(text) == {"ok": True}

    def test_prefix_and_suffix_without_fence(self):
        assert extract_json("noise before [1, 2] and after") == [1, 2]

    def test_braces_inside_strings(self):
        # The balanced scanner must ignore braces inside string literals.
        assert extract_json('garbage {"k": "a}b{c"} trailing') == {"k": "a}b{c"}

    def test_garbage_returns_none(self):
        assert extract_json("not json at all") is None

    def test_empty_returns_none(self):
        assert extract_json("") is None
        assert extract_json("   ") is None


class TestParseLineItems:
    def test_skips_invalid_rows_keeps_valid(self):
        raw = [
            {
                "description": "Plywood",
                "quantity": "2",
                "unit_price": "10.00",
                "extended_price": "20.00",
            },
            {"description": "", "quantity": "1", "unit_price": "1", "extended_price": "1"},
            {"quantity": "5"},  # missing description entirely
        ]
        items = parse_line_items(raw)
        assert len(items) == 1
        assert items[0].description == "Plywood"

    def test_non_list_returns_empty(self):
        assert parse_line_items({"not": "a list"}) == []
        assert parse_line_items(None) == []


class TestParseHeaderTotals:
    def test_header_fallback_on_bad_data(self):
        assert parse_header(None).supplier_name == "Unknown"
        assert parse_header({"no_supplier": 1}).supplier_name == "Unknown"

    def test_header_valid(self):
        assert parse_header({"supplier_name": "ABC"}).supplier_name == "ABC"

    def test_totals_fallback(self):
        assert parse_totals(None).total is None
        assert parse_totals({"total": "100.00"}).total == Decimal("100.00")


class TestComputeConfidence:
    def test_empty_is_penalised(self):
        assert compute_confidence([], 0.6) == round(0.6 * 0.4, 3)

    def test_blends_base_and_item_confidence(self):
        items = [
            LineItem(
                description="x",
                quantity=Decimal("1"),
                unit_price=Decimal("1"),
                extended_price=Decimal("1"),
                confidence=1.0,
            )
        ]
        # 0.4 * 0.9 + 0.6 * 1.0
        assert compute_confidence(items, 0.9) == 0.96
