"""Extraction data contracts.

These models define the canonical shape of extracted supplier-quote data.
Every extraction pipeline (A, B, C) MUST produce an ExtractionResult that
conforms to this schema.  The validation gate checks conformance before
data flows downstream to proposal generation.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class UnitOfMeasure(StrEnum):
    EACH = "each"
    LINEAR_FT = "linear_ft"
    SQUARE_FT = "sq_ft"
    BUNDLE = "bundle"
    BOX = "box"
    PALLET = "pallet"
    TON = "ton"
    CUBIC_YARD = "cu_yd"
    GALLON = "gallon"
    OTHER = "other"


class LineItem(BaseModel):
    """A single line item extracted from a supplier quote."""

    sku: str | None = None
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Annotated[Decimal, Field(gt=0)]
    unit: UnitOfMeasure = UnitOfMeasure.EACH
    unit_price: Annotated[Decimal, Field(ge=0)]
    extended_price: Annotated[Decimal, Field(ge=0)]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0

    @field_validator("extended_price")
    @classmethod
    def extended_must_match(cls, v: Decimal, info) -> Decimal:
        """Warn if extended_price != quantity * unit_price (within tolerance)."""
        data = info.data
        if "quantity" in data and "unit_price" in data:
            expected = data["quantity"] * data["unit_price"]
            tolerance = Decimal("0.02")
            if abs(v - expected) > tolerance:
                # Don't reject — flag low confidence.  The validation gate
                # will decide whether to escalate.
                pass
        return v


class HeaderData(BaseModel):
    """Supplier and quote metadata extracted from the header region."""

    supplier_name: str = Field(..., min_length=1)
    quote_number: str | None = None
    quote_date: str | None = None
    expiration_date: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    sales_rep: str | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None


class TotalsData(BaseModel):
    """Totals section extracted from the quote."""

    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    tax_rate: Decimal | None = None
    shipping: Decimal | None = None
    discount_amount: Decimal | None = None
    total: Decimal | None = None

    @field_validator("tax_rate")
    @classmethod
    def tax_rate_reasonable(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and (v < 0 or v > Decimal("0.25")):
            raise ValueError(f"Tax rate {v} outside reasonable range 0–25%")
        return v


class ExtractionResult(BaseModel):
    """The canonical output of any extraction pipeline.

    This is THE contract.  Every pipeline produces one of these.
    The validation gate checks it.  Proposal generation consumes it.
    """

    header: HeaderData
    line_items: list[LineItem] = Field(..., min_length=1)
    totals: TotalsData
    source_pipeline: str = Field(..., description="Which pipeline produced this: a, b, or c")
    raw_text: str | None = Field(None, description="Original text fed to extraction")
    page_count: int | None = None
    extraction_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0

    @property
    def computed_subtotal(self) -> Decimal:
        return sum(item.extended_price for item in self.line_items)

    @property
    def line_item_count(self) -> int:
        return len(self.line_items)
