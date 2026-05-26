"use client";

import { useState } from "react";
import ReviewSurface from "../components/ReviewSurface";

type QuoteStatus = "idle" | "uploading" | "processing" | "review" | "done";

export default function Home() {
  const [status, setStatus] = useState<QuoteStatus>("idle");
  const [envelopeId, setEnvelopeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus("uploading");
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/quotes", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);

      const data = await res.json();
      setEnvelopeId(data.envelope_id);
      setStatus("processing");

      // Poll for completion (simplified)
      setTimeout(() => setStatus("review"), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("idle");
    }
  };

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Proposal Engine</h1>
      <p className="text-gray-600 mb-8">
        Upload a supplier quote to generate a contractor proposal.
      </p>

      {status === "idle" && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
          <label className="cursor-pointer">
            <span className="text-lg text-gray-500">
              Drop a supplier quote PDF here, or click to browse
            </span>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={handleUpload}
              className="hidden"
            />
          </label>
        </div>
      )}

      {status === "uploading" && (
        <div className="text-center py-12">
          <p className="text-lg">Uploading quote...</p>
        </div>
      )}

      {status === "processing" && (
        <div className="text-center py-12">
          <p className="text-lg">Extracting data from quote...</p>
          <p className="text-sm text-gray-500 mt-2">
            Envelope: {envelopeId}
          </p>
        </div>
      )}

      {status === "review" && envelopeId && (
        <ReviewSurface
          envelopeId={envelopeId}
          onApprove={() => setStatus("done")}
          onReject={() => setStatus("idle")}
        />
      )}

      {status === "done" && (
        <div className="text-center py-12">
          <p className="text-lg text-green-600 font-semibold">
            Proposal approved and ready for delivery.
          </p>
          <button
            onClick={() => {
              setStatus("idle");
              setEnvelopeId(null);
            }}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Process Another Quote
          </button>
        </div>
      )}

      {error && (
        <p className="mt-4 text-red-600">{error}</p>
      )}
    </main>
  );
}
