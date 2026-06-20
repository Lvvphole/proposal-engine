"""Proposal Builder — turns a validated extraction into a priced proposal.

This is the stage that makes the product a *proposal* generator rather than an
extraction reviewer: it applies the contractor's markup (default + per-category
where a category is known), computes tax on the marked-up subtotal using the
quote's tax rate, and attaches payment/delivery terms.

Pure and deterministic (no I/O, no LLM) so it is trivially testable. All money
is ``Decimal`` and quantized to cents with banker-free half-up rounding
(ADR-002).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from contracts.contractor import ContractorProfile
from contracts.extraction import ExtractionResult, LineItem
from contracts.proposal import Proposal, ProposalLineItem

_CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    """Quantize to cents, rounding half up."""
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _markup_for(item: LineItem, contractor: ContractorProfile) -> Decimal:
    """Resolve the markup fraction for a line item.

    Uses a per-category override when the item exposes a category attribute
    that the contractor has configured; otherwise the contractor default.
    (``LineItem`` has no category today, so this resolves to the default — the
    hook is here so per-category pricing works once categories are extracted.)
    """
    category = getattr(item, "category", None)
    if category and category in contractor.category_markups:
        return Decimal(str(contractor.category_markups[category]))
    return Decimal(str(contractor.default_markup_pct))


def build_proposal(extraction: ExtractionResult, contractor: ContractorProfile) -> Proposal:
    """Apply contractor pricing to an extraction and return a Proposal."""
    proposal_items: list[ProposalLineItem] = []
    cost_subtotal = Decimal("0")
    subtotal = Decimal("0")

    for item in extraction.line_items:
        markup = _markup_for(item, contractor)
        multiplier = Decimal("1") + markup

        unit_price = _money(item.unit_price * multiplier)
        extended_price = _money(item.extended_price * multiplier)

        cost_subtotal += item.extended_price
        subtotal += extended_price

        proposal_items.append(
            ProposalLineItem(
                sku=item.sku,
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unit_cost=item.unit_price,
                markup_pct=markup,
                unit_price=unit_price,
                extended_price=extended_price,
            )
        )

    cost_subtotal = _money(cost_subtotal)
    subtotal = _money(subtotal)

    tax_rate = extraction.totals.tax_rate or Decimal("0")
    tax_amount = _money(subtotal * tax_rate)
    total = _money(subtotal + tax_amount)

    return Proposal(
        contractor_id=contractor.id if contractor.id != "default" else None,
        supplier_name=extraction.header.supplier_name,
        line_items=proposal_items,
        cost_subtotal=cost_subtotal,
        subtotal=subtotal,
        markup_amount=_money(subtotal - cost_subtotal),
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=total,
        payment_terms=contractor.payment_terms,
        delivery_terms=extraction.header.delivery_terms,
    )
