"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, BoQComparisonDTO, LineItemComparisonDTO } from "@/lib/api";
import { formatTimeRemaining, formatZAR, formatDateTime } from "@/lib/formatters";

export default function QuoteComparisonPage() {
  const params = useParams();
  const boqId = (params?.boqId as string) || "";

  const [data, setData] = useState<BoQComparisonDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Manual Override Modal
  const [overrideItem, setOverrideItem] = useState<LineItemComparisonDTO | null>(null);
  const [overridePriceRands, setOverridePriceRands] = useState<string>("");
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [savingOverride, setSavingOverride] = useState(false);
  const [autoSelecting, setAutoSelecting] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  useEffect(() => {
    loadComparison();
  }, [boqId]);

  const loadComparison = async () => {
    try {
      setLoading(true);
      const res = await api.getQuoteComparison(boqId);
      setData(res);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectQuote = async (requestId: string, quoteId: string) => {
    try {
      await api.selectQuote(requestId, quoteId);
      await loadComparison();
    } catch (err: any) {
      alert("Failed to select quote: " + err.message);
    }
  };

  const handleAutoSelectBestQuotes = async () => {
    try {
      setAutoSelecting(true);
      setActionNotice(null);
      const res = await api.autoSelectBestQuotes(boqId);
      setActionNotice(`✓ ${res.message}`);
      await loadComparison();
    } catch (err: any) {
      alert("Auto-selection failed: " + err.message);
    } finally {
      setAutoSelecting(false);
    }
  };

  const handleSimulateQuotes = async () => {
    try {
      setSimulating(true);
      setActionNotice(null);
      const res = await api.simulateBoqQuotes(boqId);
      setActionNotice(`✓ Generated simulated supplier quotes!`);
      await loadComparison();
    } catch (err: any) {
      alert("Simulation failed: " + err.message);
    } finally {
      setSimulating(false);
    }
  };

  const openOverrideModal = (item: LineItemComparisonDTO) => {
    setOverrideItem(item);
    setOverridePriceRands(item.final_price_minor ? (item.final_price_minor / 100).toString() : "");
    setOverrideReason("");
  };

  const handleSaveOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideItem || !overridePriceRands || !overrideReason.trim()) return;

    const minorCents = Math.round(parseFloat(overridePriceRands) * 100);
    if (isNaN(minorCents) || minorCents < 0) {
      alert("Please enter a valid price amount.");
      return;
    }

    try {
      setSavingOverride(true);
      await api.overridePrice(boqId, overrideItem.line_item_id, minorCents, overrideReason.trim());
      setOverrideItem(null);
      await loadComparison();
    } catch (err: any) {
      alert("Failed to save price override: " + err.message);
    } finally {
      setSavingOverride(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-sm text-slate-500">Loading quote comparison matrix...</div>;
  }

  if (error || !data) {
    return <div className="p-8 text-center text-sm text-red-600 bg-red-50">{error || "Comparison data unavailable"}</div>;
  }

  const unpricedCount = data.line_items.filter((i) => !i.final_price_minor).length;

  return (
    <div className="space-y-6">
      {/* Header & Step Navigation */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs text-slate-500 font-medium mb-1">
              <span>Tender Ref: <strong className="text-slate-800">{data.title}</strong></span>
              <span>&bull;</span>
              <span>Region: <strong className="text-slate-800">{data.region}</strong></span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Supplier Quote Comparison Matrix</h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleAutoSelectBestQuotes}
              disabled={autoSelecting}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow transition flex items-center space-x-1.5 disabled:opacity-50"
            >
              <span>⚡</span>
              <span>{autoSelecting ? "Selecting..." : "Auto-Select Best Prices"}</span>
            </button>
            <button
              onClick={handleSimulateQuotes}
              disabled={simulating}
              className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow transition disabled:opacity-50 flex items-center space-x-1"
            >
              <span>🎲</span>
              <span>{simulating ? "Simulating..." : "Simulate Quotes (Demo)"}</span>
            </button>
            <button
              onClick={loadComparison}
              className="px-3 py-2 rounded-xl text-slate-600 hover:bg-slate-50 font-semibold text-xs border border-slate-200"
            >
              🔄 Refresh
            </button>
            <a
              href={`/contractor/boqs/${data.boq_id}/review`}
              className="px-3.5 py-2 rounded-xl text-slate-600 hover:bg-slate-50 font-semibold text-xs border border-slate-200"
            >
              &larr; 1. Review
            </a>
            <a
              href={`/contractor/boqs/${data.boq_id}/export`}
              className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow transition"
            >
              3. Export Priced BoQ &rarr;
            </a>
          </div>
        </div>

        {actionNotice && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-bold flex items-center justify-between">
            <span>{actionNotice}</span>
            <button onClick={() => setActionNotice(null)} className="text-emerald-600 hover:text-emerald-800 font-bold">
              &times;
            </button>
          </div>
        )}

        {/* Pricing Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-100">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="text-xs font-semibold text-slate-500">Total Validated / Selected Total</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1 font-mono">{formatZAR(data.total_priced_minor)}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Fixed for submission schedule</div>
          </div>
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="text-xs font-semibold text-slate-500">Estimated Market Total</div>
            <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">
              {formatZAR(data.total_estimated_minor + data.total_priced_minor)}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Based on lowest quotes &amp; benchmarks</div>
          </div>
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div className="text-xs font-semibold text-slate-500">Priced Progress</div>
            <div className="text-2xl font-bold text-blue-600 mt-1">
              {data.line_items.filter((i) => i.final_price_minor).length} / {data.line_items.length} items
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              {unpricedCount === 0 ? "✓ 100% Ready for Export" : `${unpricedCount} item(s) unpriced`}
            </div>
          </div>
        </div>
      </div>

      {/* Line Items & Quotes Comparison Cards */}
      <div className="space-y-4">
        {data.line_items.map((item, idx) => {
          const hasQuotes = item.quotes && item.quotes.length > 0;
          const deadlineStatus = item.response_deadline ? formatTimeRemaining(item.response_deadline) : null;

          // Benchmark Variance Calculation
          let variancePct: number | null = null;
          if (item.final_price_minor && item.benchmark_min_minor && item.benchmark_max_minor) {
            const avgBenchmark = (item.benchmark_min_minor + item.benchmark_max_minor) / 2;
            variancePct = Math.round(((item.final_price_minor - avgBenchmark) / avgBenchmark) * 100);
          }

          return (
            <div
              key={item.line_item_id}
              className={`bg-white rounded-2xl border p-5 shadow-sm space-y-4 transition ${
                item.final_price_minor ? "border-emerald-200 ring-1 ring-emerald-500/10" : "border-slate-200"
              }`}
            >
              {/* Item Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-slate-400">#{idx + 1}</span>
                    <span className="font-bold text-slate-900 text-sm">{item.description}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium capitalize">
                      {item.category.replace("-", " ")}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-3">
                    <span>Quantity: <strong className="text-slate-800">{item.quantity.toLocaleString()} {item.unit}</strong></span>
                    {item.benchmark_min_minor && item.benchmark_max_minor && (
                      <span className="font-mono text-[11px] text-slate-500">
                        SA Benchmark: {formatZAR(item.benchmark_min_minor)} – {formatZAR(item.benchmark_max_minor)}
                      </span>
                    )}
                    {variancePct !== null && (
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          variancePct <= 0
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {variancePct <= 0 ? `${Math.abs(variancePct)}% below SA Guide` : `+${variancePct}% above SA Guide`}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {item.final_price_minor ? (
                    <div className="text-right">
                      <div className="text-[10px] uppercase font-bold text-emerald-700 tracking-wider">
                        {item.pricing_status === "manually_priced" ? "Manual Override" : "Selected Price"}
                      </div>
                      <div className="text-base font-extrabold text-emerald-700 font-mono">
                        {formatZAR(item.final_price_minor)} <span className="text-xs font-normal text-slate-500">/ {item.unit}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-medium font-mono">
                        Line Total: {formatZAR(item.final_price_minor * item.quantity)}
                      </div>
                    </div>
                  ) : (
                    <span className="text-xs px-2.5 py-1 rounded bg-amber-50 text-amber-700 font-semibold border border-amber-200">
                      Unpriced
                    </span>
                  )}

                  <button
                    onClick={() => openOverrideModal(item)}
                    className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold"
                  >
                    Manual Override
                  </button>
                </div>
              </div>

              {/* Quotes Section */}
              {hasQuotes ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                    <span>Received Supplier Quotes ({item.quotes.length}):</span>
                    {deadlineStatus && (
                      <span className={`text-[11px] font-medium ${deadlineStatus.isExpired ? "text-slate-400" : "text-amber-600"}`}>
                        Window: {deadlineStatus.text}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {item.quotes.map((q) => {
                      const isLowest = item.lowest_quote?.id === q.id;
                      const isFastest = item.fastest_quote?.id === q.id;
                      const isSelected = q.is_selected;

                      return (
                        <div
                          key={q.id}
                          className={`p-4 rounded-xl border relative flex flex-col justify-between transition ${
                            isSelected
                              ? "bg-emerald-50/60 border-emerald-500 ring-2 ring-emerald-500/20"
                              : "bg-slate-50/60 border-slate-200 hover:bg-white"
                          }`}
                        >
                          <div className="space-y-2">
                            {/* Badges */}
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-1">
                                {isLowest && (
                                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 uppercase">
                                    ★ Lowest Price
                                  </span>
                                )}
                                {isFastest && !isLowest && (
                                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 uppercase">
                                    ⚡ Fastest Lead
                                  </span>
                                )}
                              </div>
                              {isSelected && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-600 text-white">
                                  ✓ Selected
                                </span>
                              )}
                            </div>

                            {/* Supplier Name */}
                            <div className="font-bold text-slate-900 text-xs">
                              {q.supplier_name || "Verified Supplier"}
                            </div>

                            {/* Pricing */}
                            <div>
                              <div className="text-lg font-extrabold text-slate-900 font-mono">
                                {formatZAR(q.unit_price_minor)}
                                <span className="text-xs font-normal text-slate-500"> / {item.unit}</span>
                              </div>
                              <div className="text-[11px] text-slate-500 font-mono">
                                Line Total: {formatZAR(q.total_price_minor)}
                              </div>
                            </div>

                            {/* Lead Time & Notes */}
                            <div className="text-[11px] text-slate-600 space-y-0.5 pt-1 border-t border-slate-200/60">
                              {q.lead_time_days && (
                                <div>Lead Time: <strong className="text-slate-800">{q.lead_time_days} days</strong></div>
                              )}
                              {q.notes && (
                                <div className="italic text-slate-500 line-clamp-2">&ldquo;{q.notes}&rdquo;</div>
                              )}
                            </div>
                          </div>

                          {/* Selection Action Button */}
                          <div className="mt-3 pt-2">
                            {isSelected ? (
                              <button
                                disabled
                                className="w-full py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-bold shadow-sm cursor-default"
                              >
                                Winning Price Active
                              </button>
                            ) : (
                              <button
                                onClick={() => item.quote_request_id && handleSelectQuote(item.quote_request_id, q.id)}
                                className="w-full py-1.5 rounded-lg bg-white hover:bg-slate-900 hover:text-white text-slate-700 border border-slate-300 text-xs font-bold transition shadow-sm"
                              >
                                Select This Quote
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="bg-slate-50 rounded-xl p-4 text-center text-xs text-slate-500 space-y-1">
                  <div>No supplier quotes received yet.</div>
                  {deadlineStatus && !deadlineStatus.isExpired && (
                    <div className="text-amber-700 font-medium">
                      Response window active — {deadlineStatus.text}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Manual Override Modal */}
      {overrideItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Manual Price Override</h3>
              <button
                onClick={() => setOverrideItem(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveOverride} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-500 mb-1">Line Item</label>
                <div className="font-bold text-slate-900 text-sm">{overrideItem.description}</div>
                <div className="text-slate-500 font-mono mt-0.5">
                  Qty: {overrideItem.quantity} {overrideItem.unit}
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Override Unit Rate (ZAR / {overrideItem.unit}) <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-xs text-slate-500 font-bold">R</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    placeholder="e.g. 120.00"
                    value={overridePriceRands}
                    onChange={(e) => setOverridePriceRands(e.target.value)}
                    className="w-full text-sm font-bold pl-8 pr-3 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Audit Justification / Reason <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="e.g. Verified existing warehouse inventory rate from Project B."
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  This explanation is recorded in the immutable tender audit trail.
                </p>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setOverrideItem(null)}
                  className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingOverride}
                  className="px-5 py-2 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 shadow"
                >
                  {savingOverride ? "Saving..." : "Save Override"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
