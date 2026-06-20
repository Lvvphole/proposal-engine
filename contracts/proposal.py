"""Proposal contracts — the contractor-facing output of the system.

A ``Proposal`` is what the Proposal Builder produces from a validated
``ExtractionResult`` by applying the contractor's markup, tax, and terms.
It is the customer-ready artifact the Review Surface presents for approval.

All monetary values are ``Decimal`` (see ADR-002).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProposalLineItem(BaseModel):
    """A single priced line on the contractor proposal.

    Carries both the supplier cost and the marked-up customer price so the
    Review Surface can show the margin transparently.
    """

    sku: str | None = None
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal  # supplier's unit price
    markup_pct: Decimal  # applied markup as a fraction, e.g. 0.20
    unit_price: Decimal  # customer-facing unit price (cost × (1 + markup))
    extended_price: Decimal  # customer-facing line total


class Proposal(BaseModel):
    """A contractor-ready proposal derived from an extraction."""

    contractor_id: str | None = None
    supplier_name: str = ""
    line_items: list[ProposalLineItem] = Field(default_factory=list)

    cost_subtotal: Decimal  # sum of supplier extended prices
    subtotal: Decimal  # sum of marked-up extended prices
    markup_amount: Decimal  # subtotal − cost_subtotal
    tax_rate: Decimal  # fraction applied to the marked-up subtotal
    tax_amount: Decimal
    total: Decimal  # subtotal + tax_amount

    payment_terms: str = "Due on completion"
    delivery_terms: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def line_item_count(self) -> int:
        return len(self.line_items)
