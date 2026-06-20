"""Classifier agent — routes a quote to the right extraction pipeline.

Runs first in the orchestrator: inspects the document and decides whether it
is a clean table (Pipeline A), semi-structured (B), or unstructured (C).
Low-confidence or unparseable results fall back to Pipeline C, the broadest
extractor.
"""

from __future__ import annotations

import structlog
from pydantic import ValidationError

from contracts.classifier import ClassificationResult, QuoteFormat
from contracts.envelope import Envelope
from core.config import get_config
from core.llm import call_llm
from harness.document_preparer import build_user_content
from pipelines.parsing import extract_json

logger = structlog.get_logger()


def _fallback(reason: str) -> ClassificationResult:
    return ClassificationResult(
        format=QuoteFormat.UNSTRUCTURED_FREETEXT,
        pipeline="c",
        confidence=0.0,
        reasoning=reason[:500],
    )


async def classify(envelope: Envelope) -> ClassificationResult:
    """Classify a quote and return the routing decision.

    Never raises on bad model output — returns a Pipeline C fallback instead,
    so a flaky classifier degrades gracefully rather than failing the run.
    """
    config = get_config()
    response = await call_llm(
        system=_CLASSIFIER_PROMPT,
        messages=[{"role": "user", "content": build_user_content(envelope)}],
        model=config.classifier_model,
        max_tokens=1024,
        envelope=envelope,
        agent_name="classifier",
    )

    data = extract_json(response)
    if not isinstance(data, dict):
        logger.warning("classify_unparseable", envelope_id=envelope.id)
        return _fallback("Classifier output was not parseable JSON.")

    try:
        result = ClassificationResult.model_validate(data)
    except ValidationError as exc:
        logger.warning("classify_invalid", envelope_id=envelope.id, error=str(exc))
        return _fallback("Classifier output failed contract validation.")

    # Below the fallback threshold, route to C regardless of the stated pipeline.
    if result.needs_fallback:
        logger.info(
            "classify_low_confidence_fallback",
            envelope_id=envelope.id,
            confidence=result.confidence,
        )
        return result.model_copy(update={"pipeline": "c"})

    logger.info(
        "classified",
        envelope_id=envelope.id,
        pipeline=result.pipeline,
        confidence=result.confidence,
    )
    return result


_CLASSIFIER_PROMPT = """You are a document classification agent for a contractor \
proposal system. Analyze the supplier quote and determine its format.

Classify into exactly one category:
- "structured_table" (pipeline "a"): clean tabular data with aligned columns for \
SKU, description, quantity, unit price, extended price.
- "semi_structured" (pipeline "b"): some structure but not a clean table — \
inconsistent columns, merged cells, or tables embedded in prose.
- "unstructured" (pipeline "c"): free-form text, handwritten or photographed price \
sheets, or email bodies with inline pricing.

Return ONLY a JSON object:
{
  "format": "structured_table | semi_structured | unstructured",
  "pipeline": "a | b | c",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "detected_supplier": "supplier name or null",
  "page_count": <int or null>,
  "has_images": <true|false>
}"""
