"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

interface ReviewSurfaceProps {
  envelopeId: string;
  onApprove: () => void;
  onReject: () => void;
}

interface LineItem {
  sku: string | null;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  extended_price: number;
  confidence: number;
}

interface Extraction {
  header: {
    supplier_name: string;
    quote_number: string | null;
    quote_date: string | null;
  };
  line_items: LineItem[];
  totals: {
    subtotal: number | null;
    tax_amount: number | null;
    total: number | null;
  };
  quality_score: number;
}

interface Proposal {
  supplier_name: string;
  cost_subtotal: string;
  subtotal: string;
  markup_amount: string;
  tax_rate: string;
  tax_amount: string;
  total: string;
  payment_terms: string;
  delivery_terms: string | null;
}

const money = (v: number | string | null | undefined) =>
  v === null || v === undefined ? "—" : `$${Number(v).toFixed(2)}`;

export default function ReviewSurface({
  envelopeId,
  onApprove,
  onReject,
}: ReviewSurfaceProps) {
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/api/quotes/${envelopeId}/extraction`);
        if (!res.ok) throw new Error(`Failed to load extraction (${res.status})`);
        const data = (await res.json()) as Extraction;
        if (!cancelled) setExtraction(data);

        // The priced proposal is generated alongside extraction; tolerate its
        // absence rather than failing the whole surface.
        const pres = await apiFetch(`/api/quotes/${envelopeId}/proposal`);
        if (pres.ok && !cancelled) setProposal((await pres.json()) as Proposal);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load extraction");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [envelopeId]);

  const handleSubmit = async (verdict: "approved" | "rejected") => {
    setSubmitting(true);
    try {
      const res = await apiFetch(`/api/quotes/${envelopeId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verdict, notes }),
      });
      if (!res.ok) throw new Error(`Review failed (${res.status})`);
      verdict === "approved" ? onApprove() : onReject();
    } catch {
      setError("Failed to submit review");
    } finally {
      setSubmitting(false);
    }
  };

  const confidenceColor = (c: number) =>
    c >= 0.9 ? "text-green-600" : c >= 0.7 ? "text-yellow-600" : "text-red-600";

  if (error) {
    return <p className="text-red-600">{error}</p>;
  }

  if (!extraction) {
    return <p className="text-gray-500 py-12 text-center">Loading extraction…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Review Extraction</h2>
        <span className="text-sm text-gray-500">
          Quality: {(extraction.quality_score * 100).toFixed(0)}%
        </span>
      </div>

      {/* Header */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-semibold mb-2">Supplier Information</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Supplier:</span>{" "}
            {extraction.header.supplier_name}
          </div>
          <div>
            <span className="text-gray-500">Quote #:</span>{" "}
            {extraction.header.quote_number || "—"}
          </div>
          <div>
            <span className="text-gray-500">Date:</span>{" "}
            {extraction.header.quote_date || "—"}
          </div>
        </div>
      </div>

      {/* Line Items */}
      <div>
        <h3 className="font-semibold mb-2">Line Items</h3>
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2">SKU</th>
              <th>Description</th>
              <th className="text-right">Qty</th>
              <th className="text-right">Unit Price</th>
              <th className="text-right">Extended</th>
              <th className="text-right">Conf.</th>
            </tr>
          </thead>
          <tbody>
            {extraction.line_items.map((item, i) => (
              <tr key={i} className="border-b">
                <td className="py-2 font-mono text-xs">{item.sku || "—"}</td>
                <td>{item.description}</td>
                <td className="text-right">
                  {item.quantity} {item.unit}
                </td>
                <td className="text-right">{money(item.unit_price)}</td>
                <td className="text-right">{money(item.extended_price)}</td>
                <td className={`text-right ${confidenceColor(item.confidence)}`}>
                  {(item.confidence * 100).toFixed(0)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Totals */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="space-y-1 text-sm max-w-xs ml-auto">
          <div className="flex justify-between">
            <span>Subtotal:</span>
            <span>{money(extraction.totals.subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span>Tax:</span>
            <span>{money(extraction.totals.tax_amount)}</span>
          </div>
          <div className="flex justify-between font-bold text-base border-t pt-1">
            <span>Total:</span>
            <span>{money(extraction.totals.total)}</span>
          </div>
        </div>
      </div>

      {/* Customer Proposal (priced with contractor markup + tax) */}
      {proposal && (
        <div className="bg-blue-50 rounded-lg p-4">
          <h3 className="font-semibold mb-2">Customer Proposal</h3>
          <div className="space-y-1 text-sm max-w-xs ml-auto">
            <div className="flex justify-between text-gray-500">
              <span>Supplier cost:</span>
              <span>{money(proposal.cost_subtotal)}</span>
            </div>
            <div className="flex justify-between">
              <span>Markup:</span>
              <span>+{money(proposal.markup_amount)}</span>
            </div>
            <div className="flex justify-between">
              <span>Subtotal:</span>
              <span>{money(proposal.subtotal)}</span>
            </div>
            <div className="flex justify-between">
              <span>Tax ({(Number(proposal.tax_rate) * 100).toFixed(1)}%):</span>
              <span>{money(proposal.tax_amount)}</span>
            </div>
            <div className="flex justify-between font-bold text-base border-t pt-1">
              <span>Customer total:</span>
              <span>{money(proposal.total)}</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Terms: {proposal.payment_terms}
            {proposal.delivery_terms ? ` · ${proposal.delivery_terms}` : ""}
          </p>
        </div>
      )}

      {/* Review Controls */}
      <div>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Review notes (optional)..."
          className="w-full border rounded-lg p-3 text-sm"
          rows={3}
        />
        <div className="flex gap-3 mt-3">
          <button
            onClick={() => handleSubmit("approved")}
            disabled={submitting}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            Approve Proposal
          </button>
          <button
            onClick={() => handleSubmit("rejected")}
            disabled={submitting}
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}
