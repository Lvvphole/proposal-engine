"""Prompt assembly — composing system prompts from parts.

Each agent has a base prompt. Supplier context, contractor preferences,
few-shot examples, mode directives, and extra instructions are layered on top.
"""

from __future__ import annotations

_BASE_PROMPTS: dict[str, str] = {
    "classifier": (
        "You are a document classifier specializing in supplier quotes. "
        "Analyze the provided document and determine its format, layout, "
        "and which extraction pipeline is best suited to process it."
    ),
    "extractor": (
        "You are a data extraction specialist for supplier quotes. "
        "Extract all line items, header information, and totals with "
        "high precision. Return structured JSON matching the ExtractionResult schema."
    ),
    "validator": (
        "You are a validation agent that checks extracted quote data for "
        "consistency. Verify totals match line items, prices are reasonable, "
        "and required fields are present."
    ),
    "proposal_builder": (
        "You are a proposal generation agent for residential contractors. "
        "Transform supplier quotes into professional contractor proposals "
        "with appropriate markup, tax calculations, and delivery terms."
    ),
}

_MODE_DIRECTIVES: dict[str, str] = {
    "production": "Operate at full accuracy. Take the most conservative interpretation of ambiguous data.",
    "debug": "Include verbose reasoning in your response. Explain each decision.",
    "eval": "This is an evaluation run. Return confidence scores for every extracted field.",
}


def assemble(
    agent: str,
    *,
    supplier_context: str | None = None,
    contractor_prefs: dict | None = None,
    few_shot_examples: list[str] | None = None,
    mode: str = "production",
    extra: str | None = None,
) -> str:
    """Compose a system prompt for the given agent.

    Args:
        agent: Key in _BASE_PROMPTS (e.g. 'classifier', 'extractor').
        supplier_context: Supplier-specific notes or format hints.
        contractor_prefs: Contractor preference dict (markup_pct, tax_rate, etc.).
        few_shot_examples: List of example strings to append.
        mode: One of 'production', 'debug', 'eval'.
        extra: Freeform additional instructions appended last.

    Returns:
        The fully composed system prompt string.
    """
    if agent not in _BASE_PROMPTS:
        raise ValueError(f"Unknown agent: {agent!r}. Must be one of {list(_BASE_PROMPTS)}")

    parts: list[str] = [_BASE_PROMPTS[agent]]

    if supplier_context:
        parts.append(f"\n\nSupplier context:\n{supplier_context}")

    if contractor_prefs:
        prefs_lines = "\n".join(f"  {k}: {v}" for k, v in contractor_prefs.items())
        parts.append(f"\n\nContractor preferences:\n{prefs_lines}")

    if few_shot_examples:
        examples_block = "\n\n---\n".join(few_shot_examples)
        parts.append(f"\n\nExamples:\n{examples_block}")

    mode_directive = _MODE_DIRECTIVES.get(mode, _MODE_DIRECTIVES["production"])
    parts.append(f"\n\nMode: {mode_directive}")

    if extra:
        parts.append(f"\n\n{extra}")

    return "".join(parts)
