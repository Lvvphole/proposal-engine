"""Tests for classifier wiring, document content, and pipeline resilience.

LLM calls are mocked, so these exercise the parsing/routing logic without
hitting the API.
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import pytest

from contracts.envelope import Envelope


def _text_envelope(text: str) -> Envelope:
    return Envelope(
        source_filename="quote.txt",
        source_content_type="text/plain",
        source_bytes_b64=base64.b64encode(text.encode()).decode(),
    )


# ── Document content building ────────────────────────────────────────────


class TestBuildUserContent:
    def test_text_is_decoded(self):
        from harness.document_preparer import build_user_content

        env = _text_envelope("Supplier: ABC\nPlywood 2 @ $10")
        content = build_user_content(env)
        assert isinstance(content, str)
        assert "Supplier: ABC" in content

    def test_image_becomes_image_block(self):
        from harness.document_preparer import build_user_content

        env = Envelope(source_content_type="image/png", source_bytes_b64="QUJD")
        content = build_user_content(env)
        assert isinstance(content, list)
        assert content[0]["type"] == "image"
        assert content[0]["source"]["media_type"] == "image/png"

    def test_pdf_becomes_document_block(self):
        from harness.document_preparer import build_user_content

        env = Envelope(source_content_type="application/pdf", source_bytes_b64="QUJD")
        content = build_user_content(env)
        assert isinstance(content, list)
        assert content[0]["type"] == "document"


# ── Classifier ───────────────────────────────────────────────────────────

_VALID_CLASSIFICATION = (
    '```json\n{"format": "structured_table", "pipeline": "a", '
    '"confidence": 0.92, "reasoning": "clean table"}\n```'
)


class TestClassifier:
    @pytest.mark.asyncio
    async def test_parses_fenced_classification(self):
        from pipelines import classifier

        with patch.object(classifier, "call_llm", AsyncMock(return_value=_VALID_CLASSIFICATION)):
            result = await classifier.classify(_text_envelope("anything"))
        assert result.pipeline == "a"
        assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_unparseable_falls_back_to_c(self):
        from pipelines import classifier

        with patch.object(classifier, "call_llm", AsyncMock(return_value="sorry, no idea")):
            result = await classifier.classify(_text_envelope("anything"))
        assert result.pipeline == "c"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_low_confidence_routes_to_c(self):
        from pipelines import classifier

        low = (
            '{"format": "structured_table", "pipeline": "a", '
            '"confidence": 0.2, "reasoning": "unsure"}'
        )
        with patch.object(classifier, "call_llm", AsyncMock(return_value=low)):
            result = await classifier.classify(_text_envelope("anything"))
        # Stated pipeline "a" but below fallback threshold → routed to C.
        assert result.pipeline == "c"


# ── Pipeline resilience ──────────────────────────────────────────────────

_GOOD_EXTRACTION = """Here you go:
```json
{
  "header": {"supplier_name": "ABC Supply"},
  "line_items": [
    {"description": "Plywood", "quantity": "2", "unit_price": "10.00", "extended_price": "20.00"},
    {"description": "", "quantity": "1", "unit_price": "1", "extended_price": "1"}
  ],
  "totals": {"subtotal": "20.00", "total": "20.00"}
}
```"""


class TestPipelineResilience:
    @pytest.mark.asyncio
    async def test_pipeline_c_parses_fenced_and_skips_bad_row(self):
        from pipelines.pipeline_c import run as pc

        with patch.object(pc, "call_llm", AsyncMock(return_value=_GOOD_EXTRACTION)):
            result = await pc.run(_text_envelope("anything"))
        assert result.source_pipeline == "c"
        assert result.header.supplier_name == "ABC Supply"
        assert len(result.line_items) == 1  # the empty-description row was skipped
        assert 0.0 < result.extraction_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_pipeline_c_raises_when_no_items(self):
        from contracts.errors import ExtractionError
        from pipelines.pipeline_c import run as pc

        empty = '{"header": {"supplier_name": "X"}, "line_items": [], "totals": {}}'
        with (
            patch.object(pc, "call_llm", AsyncMock(return_value=empty)),
            pytest.raises(ExtractionError),
        ):
            await pc.run(_text_envelope("anything"))

    @pytest.mark.asyncio
    async def test_pipeline_a_three_calls_assemble(self):
        from pipelines.pipeline_a import run as pa

        responses = {
            "header_extractor": '{"supplier_name": "ABC Supply"}',
            "line_item_extractor": (
                '[{"description": "Plywood", "quantity": "2", '
                '"unit_price": "10.00", "extended_price": "20.00"}]'
            ),
            "totals_extractor": '{"subtotal": "20.00", "total": "20.00"}',
        }

        async def fake_call_llm(*, agent_name, **kwargs):
            return responses[agent_name]

        with patch.object(pa, "call_llm", side_effect=fake_call_llm):
            result = await pa.run(_text_envelope("anything"))
        assert result.source_pipeline == "a"
        assert len(result.line_items) == 1
        assert result.totals.total is not None
