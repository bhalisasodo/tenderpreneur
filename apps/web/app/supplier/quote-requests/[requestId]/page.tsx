"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, QuoteRequestDTO } from "@/lib/api";
import { formatDateTime, formatTimeRemaining, formatZAR } from "@/lib/formatters";

const LEAD_TIME_PRESETS = [
  { label: "⚡ Same Day / 24h", days: 1 },
  { label: "🚚 2-3 Days", days: 3 },
  { label: "📦 5-7 Days", days: 7 },
  { label: "🗓️ 2 Weeks", days: 14 },
];

const TERMS_PRESETS = [
  "Price includes site delivery within 50km radius.",
  "Offloading by contractor on site.",
  "Quote valid for 30 calendar days from submission.",
  "SABS / SANS compliant stock guaranteed.",
];

export default function SupplierQuoteSubmissionPage() {
  const params = useParams();
  const requestId = (params?.requestId as string) || "";
  const router = useRouter();

  const [request, setRequest] = useState<QuoteRequestDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [unitPriceRands, setUnitPriceRands] = useState<string>("");
  const [leadTimeDays, setLeadTimeDays] = useState<number>(3);
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadRequest();
  }, [requestId]);

  const loadRequest = async () => {
    try {
      setLoading(true);
      const data = await api.getSupplierQuoteRequest(requestId);
      setRequest(data);
      if (data.quotes && data.quotes.length > 0) {
        const q = data.quotes[0];
        setUnitPriceRands((q.unit_price_minor / 100).toString());
        setLeadTimeDays(q.lead_time_days || 3);
        setNotes(q.notes || "");
      }
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addTermToNotes = (term: string) => {
    setNotes((prev) => {
      if (!prev.trim()) return term;
      if (prev.includes(term)) return prev;
      return `${prev.trim()} ${term}`;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!unitPriceRands || !request) return;

    const minorCents = Math.round(parseFloat(unitPriceRands) * 100);
    if (isNaN(minorCents) || minorCents <= 0) {
      alert("Please enter a valid positive unit price.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      await api.submitSupplierQuote(
        requestId,
        minorCents,
        leadTimeDays || undefined,
        notes.trim() || undefined
      );
      setSuccess(true);
      setTimeout(() => {
        router.push("/supplier");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to submit quote");
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="bg-white rounded-2xl p-12 text-center text-xs text-slate-500 border border-slate-200">Loading quote request...</div>;
  }

  if (error && !request) {
    return <div className="bg-red-50 p-4 rounded-xl text-xs text-red-700 font-medium border border-red-200">{error}</div>;
  }

  if (!request) return null;

  const timeInfo = formatTimeRemaining(request.response_deadline);
  const qty = request.line_item_quantity || 1.0;
  const parsedPrice = parseFloat(unitPriceRands) || 0;
  const calculatedTotal = parsedPrice * qty;

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Header Back Link */}
      <div className="flex items-center justify-between">
        <a
          href="/supplier"
          className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg border border-slate-200 bg-white"
        >
          &larr; Back to Requests
        </a>
        <span className="text-xs text-slate-500 font-mono">
          Ref: #{request.id.slice(0, 8)}
        </span>
      </div>

      {/* Item Details Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-100 text-blue-800">
            {request.line_item_category?.replace("-", " ") || "Material / Trade"}
          </span>
          <span
            className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
              timeInfo.isExpired ? "bg-slate-200 text-slate-700" : timeInfo.isUrgent ? "bg-red-100 text-red-800 animate-pulse" : "bg-amber-100 text-amber-800"
            }`}
          >
            {timeInfo.text}
          </span>
        </div>

        <div>
          <span className="text-xs text-slate-400 font-medium">Requested Line Item:</span>
          <h3 className="font-bold text-slate-900 text-base leading-snug mt-0.5">
            {request.line_item_description}
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100 text-xs">
          <div>
            <span className="text-slate-500">Required Quantity:</span>
            <div className="font-bold text-slate-900 text-sm">
              {qty.toLocaleString()} {request.line_item_unit}
            </div>
          </div>
          <div>
            <span className="text-slate-500">Project Location:</span>
            <div className="font-bold text-slate-900">{request.boq_region}</div>
          </div>
        </div>
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-2xl p-4 text-xs font-bold text-center shadow-sm">
          ✓ Quote submitted successfully to contractor! Redirecting...
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4 text-xs font-medium">
          {error}
        </div>
      )}

      {/* Quote Submission Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-5">
        <h4 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-2 flex items-center justify-between">
          <span>Your Pricing &amp; Terms</span>
          <span className="text-[11px] text-slate-400 font-normal">All amounts in ZAR</span>
        </h4>

        {/* Unit Price Rate */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Unit Price Rate (ZAR / {request.line_item_unit}) <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-xs text-slate-500 font-bold">R</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              disabled={timeInfo.isExpired || submitting}
              placeholder="e.g. 115.00"
              value={unitPriceRands}
              onChange={(e) => setUnitPriceRands(e.target.value)}
              className="w-full text-base font-bold pl-8 pr-3 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none font-mono"
            />
          </div>
        </div>

        {/* Auto Calculated Total */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex items-center justify-between text-xs font-mono">
          <div>
            <span className="font-sans text-slate-600 block text-[11px]">Calculated Line Total:</span>
            <span className="text-slate-400 font-sans text-[10px]">
              {qty.toLocaleString()} {request.line_item_unit} &times; R{parsedPrice.toFixed(2)}
            </span>
          </div>
          <span className="font-black text-lg text-slate-900">
            {formatZAR(Math.round(calculatedTotal * 100))}
          </span>
        </div>

        {/* Lead Time with Quick Preset Chips */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-slate-700">
            Delivery Lead Time: <strong className="text-slate-900">{leadTimeDays} day(s)</strong>
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {LEAD_TIME_PRESETS.map((p) => (
              <button
                key={p.days}
                type="button"
                onClick={() => setLeadTimeDays(p.days)}
                disabled={timeInfo.isExpired || submitting}
                className={`py-1.5 px-2.5 rounded-lg text-xs font-semibold border transition ${
                  leadTimeDays === p.days
                    ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Notes & Quick Terms Chips */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-slate-700">
            Notes / Inclusions / Delivery Terms
          </label>
          <div className="flex flex-wrap gap-1.5 mb-1.5">
            {TERMS_PRESETS.map((term, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => addTermToNotes(term)}
                disabled={timeInfo.isExpired || submitting}
                className="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-1 rounded-md border border-slate-200 transition"
              >
                + {term}
              </button>
            ))}
          </div>
          <textarea
            rows={3}
            disabled={timeInfo.isExpired || submitting}
            placeholder="e.g. Price includes delivery to site. Offloading by contractor."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full text-xs p-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={timeInfo.isExpired || submitting}
            className="w-full py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-md transition disabled:opacity-50 flex items-center justify-center space-x-2"
          >
            {submitting ? (
              <span>Submitting Quote to Contractor...</span>
            ) : timeInfo.isExpired ? (
              <span>Deadline Passed — Closed</span>
            ) : (
              <span>Submit Competitive Quote &rarr;</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
