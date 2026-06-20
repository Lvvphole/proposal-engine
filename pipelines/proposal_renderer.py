"""Proposal renderer — turns a priced ``Proposal`` into a sendable document.

Produces a clean, self-contained, print-friendly HTML proposal (inline CSS, no
assets) that a contractor can review and print/save as PDF to send to their
customer. It deliberately shows only the **customer-facing** figures
(per-line price and totals) — the supplier cost and the contractor's markup are
internal margin and are not rendered here.
"""

from __future__ import annotations

import html
from datetime import datetime
from decimal import Decimal

from contracts.contractor import ContractorProfile
from contracts.proposal import Proposal, ProposalLineItem


def _money(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _qty(amount: Decimal) -> str:
    # Drop trailing zeros so "2.00" renders as "2", but keep "2.5".
    normalized = amount.normalize()
    return f"{normalized:f}"


def _line_rows(items: list[ProposalLineItem]) -> str:
    rows = []
    for item in items:
        sku = f"<span class='sku'>{html.escape(item.sku)}</span> " if item.sku else ""
        rows.append(
            "<tr>"
            f"<td>{sku}{html.escape(item.description)}</td>"
            f"<td class='num'>{_qty(item.quantity)} {html.escape(item.unit)}</td>"
            f"<td class='num'>{_money(item.unit_price)}</td>"
            f"<td class='num'>{_money(item.extended_price)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _company_name(contractor: ContractorProfile | None) -> str:
    if contractor is None:
        return "Proposal"
    return contractor.company or contractor.name or "Proposal"


def render_proposal_html(proposal: Proposal, contractor: ContractorProfile | None = None) -> str:
    """Render a customer-ready HTML proposal document."""
    company = html.escape(_company_name(contractor))
    date_str = (proposal.generated_at or datetime.now()).strftime("%B %d, %Y")
    tax_pct = (proposal.tax_rate * Decimal("100")).normalize()

    contact_bits = []
    if contractor is not None:
        if contractor.phone:
            contact_bits.append(html.escape(contractor.phone))
        if contractor.email:
            contact_bits.append(html.escape(contractor.email))
        if contractor.license_number:
            contact_bits.append(f"Lic. {html.escape(contractor.license_number)}")
    contact = " · ".join(contact_bits)

    delivery = (
        f"<p><strong>Delivery:</strong> {html.escape(proposal.delivery_terms)}</p>"
        if proposal.delivery_terms
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Proposal — {company}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         color: #1a1a1a; max-width: 720px; margin: 2rem auto; padding: 0 1.5rem; }}
  header {{ display: flex; justify-content: space-between; align-items: baseline;
            border-bottom: 2px solid #1a1a1a; padding-bottom: .75rem; }}
  header h1 {{ font-size: 1.5rem; margin: 0; }}
  .meta {{ text-align: right; font-size: .85rem; color: #555; }}
  .contact {{ font-size: .85rem; color: #555; margin-top: .25rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; font-size: .95rem; }}
  th, td {{ text-align: left; padding: .5rem .25rem; border-bottom: 1px solid #e2e2e2; }}
  th.num, td.num {{ text-align: right; white-space: nowrap; }}
  .sku {{ font-family: ui-monospace, monospace; font-size: .8rem; color: #777; }}
  .totals {{ width: 280px; margin-left: auto; font-size: .95rem; }}
  .totals div {{ display: flex; justify-content: space-between; padding: .2rem 0; }}
  .totals .grand {{ font-weight: 700; font-size: 1.1rem; border-top: 2px solid #1a1a1a;
                    padding-top: .4rem; margin-top: .2rem; }}
  .terms {{ margin-top: 2rem; font-size: .9rem; color: #333; }}
  footer {{ margin-top: 2rem; font-size: .75rem; color: #999; }}
  @media print {{ body {{ margin: 0; }} }}
</style>
</head>
<body>
  <header>
    <div>
      <h1>{company}</h1>
      {f'<div class="contact">{contact}</div>' if contact else ""}
    </div>
    <div class="meta">
      <div><strong>Proposal</strong></div>
      <div>{date_str}</div>
    </div>
  </header>

  <table>
    <thead>
      <tr>
        <th>Description</th>
        <th class="num">Qty</th>
        <th class="num">Unit Price</th>
        <th class="num">Amount</th>
      </tr>
    </thead>
    <tbody>
      {_line_rows(proposal.line_items)}
    </tbody>
  </table>

  <div class="totals">
    <div><span>Subtotal</span><span>{_money(proposal.subtotal)}</span></div>
    <div><span>Tax ({tax_pct:f}%)</span><span>{_money(proposal.tax_amount)}</span></div>
    <div class="grand"><span>Total</span><span>{_money(proposal.total)}</span></div>
  </div>

  <div class="terms">
    <p><strong>Payment terms:</strong> {html.escape(proposal.payment_terms)}</p>
    {delivery}
  </div>

  <footer>Generated {date_str}. This proposal is valid for 30 days.</footer>
</body>
</html>"""
