"use client";

import { useState } from "react";

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

export default function ReviewSurface({
  envelopeId,
  onApprove,
  onReject,
}: ReviewSurfaceProps) {
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Placeholder data — production fetches from API
  const extraction = {
    header: {
      supplier_name: "ABC Building Supply",
      quote_number: "Q-2024-1234",
      quote_date: "2024-06-15",
    },
    line_items: [
      {
        sku: "PLY-CDX-12",
        description: 'CDX Plywood 1/2" 4x8',
        quantity: 150,
        unit: "each",
        unit_price: 28.75,
        extended_price: 4312.5,
        confidence: 0.95,
      },
      {
        sku: "NAL-COIL-1",
        description: 'Coil Nails 1-1/4"',
        quantity: 10,
        unit: "box",
        unit_price: 42.0,
        extended_price: 420.0,
        confidence: 0.92,
      },
    ] as LineItem[],
    totals: {
      subtotal: 4732.5,
      tax_amount: 331.28,
      total: 5063.78,
    },
    quality_score: 0.91,
  };

  const handleSubmit = async (verdict: "approved" | "rejected") => {
    setSubmitting(true);
    try {
      await fetch(`/api/quotes/${envelopeId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verdict, notes }),
      });
      verdict === "approved" ? onApprove() : onReject();
    } catch {
      alert("Failed to submit review");
    } finally {
      setSubmitting(false);
    }
  };

  const confidenceColor = (c: number) =>
    c >= 0.9 ? "text-green-600" : c >= 0.7 ? "text-yellow-600" : "text-red-600";

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
            {extraction.header.quote_number}
          </div>
          <div>
            <span className="text-gray-500">Date:</span>{" "}
            {extraction.header.quote_date}
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
                <td className="text-right">${item.unit_price.toFixed(2)}</td>
                <td className="text-right">${item.extended_price.toFixed(2)}</td>
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
            <span>${extraction.totals.subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span>Tax:</span>
            <span>${extraction.totals.tax_amount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between font-bold text-base border-t pt-1">
            <span>Total:</span>
            <span>${extraction.totals.total.toFixed(2)}</span>
          </div>
        </div>
      </div>

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
