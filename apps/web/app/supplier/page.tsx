"use client";

import { useEffect, useState } from "react";
import { api, AuthSession, QuoteRequestDTO } from "../../lib/api";
import { formatDateTime, formatTimeRemaining, formatZAR } from "../../lib/formatters";

export default function SupplierDashboard() {
  const [requests, setRequests] = useState<QuoteRequestDTO[]>([]);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "pending" | "submitted" | "closed">("all");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [reqs, me] = await Promise.all([
        api.getSupplierQuoteRequests(),
        api.getMe().catch(() => null),
      ]);
      setRequests(reqs);
      setSession(me);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredRequests = requests.filter((req) => {
    const timeInfo = formatTimeRemaining(req.response_deadline);
    const hasMyQuote = req.quotes && req.quotes.length > 0;

    if (statusFilter === "pending") return !hasMyQuote && !timeInfo.isExpired;
    if (statusFilter === "submitted") return hasMyQuote;
    if (statusFilter === "closed") return timeInfo.isExpired;
    return true;
  });

  const pendingCount = requests.filter((r) => (!r.quotes || r.quotes.length === 0) && !formatTimeRemaining(r.response_deadline).isExpired).length;
  const submittedCount = requests.filter((r) => r.quotes && r.quotes.length > 0).length;

  return (
    <div className="space-y-5">
      {/* Supplier Identity Banner */}
      {session && (
        <div className="bg-gradient-to-r from-slate-900 to-blue-950 text-white p-5 rounded-2xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-800 text-blue-200">
                Supplier Portal
              </span>
              <span className="text-xs text-slate-300 font-semibold">{session.organisation.region || "KwaZulu-Natal"}</span>
            </div>
            <h2 className="text-lg font-bold">{session.organisation.legal_name}</h2>
            <p className="text-xs text-slate-400">
              Logged in as: <strong className="text-white">{session.user.name}</strong> ({session.user.email})
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <div className="text-right sm:text-right bg-white/10 px-3.5 py-2 rounded-xl border border-white/10">
              <div className="text-xs text-blue-200">Active Requests</div>
              <div className="text-lg font-black text-white">{requests.length}</div>
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex items-center space-x-1.5 overflow-x-auto text-xs font-semibold">
          <button
            onClick={() => setStatusFilter("all")}
            className={`px-3 py-1.5 rounded-lg transition ${
              statusFilter === "all" ? "bg-slate-900 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            All Requests ({requests.length})
          </button>
          <button
            onClick={() => setStatusFilter("pending")}
            className={`px-3 py-1.5 rounded-lg transition ${
              statusFilter === "pending" ? "bg-amber-600 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            ⏳ Needs Quote ({pendingCount})
          </button>
          <button
            onClick={() => setStatusFilter("submitted")}
            className={`px-3 py-1.5 rounded-lg transition ${
              statusFilter === "submitted" ? "bg-emerald-600 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            ✓ Quotes Submitted ({submittedCount})
          </button>
          <button
            onClick={() => setStatusFilter("closed")}
            className={`px-3 py-1.5 rounded-lg transition ${
              statusFilter === "closed" ? "bg-slate-700 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            ⏰ Closed
          </button>
        </div>

        <button
          onClick={loadData}
          className="text-xs text-slate-600 hover:text-slate-900 font-semibold px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition self-start sm:self-auto"
        >
          🔄 Refresh
        </button>
      </div>

      {loading ? (
        <div className="bg-white rounded-2xl p-12 text-center text-xs text-slate-500 border border-slate-200">
          Loading quote requests...
        </div>
      ) : error ? (
        <div className="bg-red-50 p-4 rounded-xl text-xs text-red-700 font-medium border border-red-200">
          {error}
        </div>
      ) : filteredRequests.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-2 shadow-sm">
          <div className="text-3xl">📭</div>
          <h4 className="font-bold text-slate-800 text-sm">No Matching Quote Requests</h4>
          <p className="text-xs text-slate-500 max-w-xs mx-auto">
            You currently have no quote requests in this view. When contractors broadcast RFQs in your trade category and region, they will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredRequests.map((req) => {
            const timeInfo = formatTimeRemaining(req.response_deadline);
            const myQuote = req.quotes && req.quotes.length > 0 ? req.quotes[0] : null;
            const isSelected = myQuote?.is_selected;

            return (
              <a
                key={req.id}
                href={`/supplier/quote-requests/${req.id}`}
                className={`block bg-white rounded-2xl border p-4 shadow-sm transition hover:shadow-md hover:border-slate-300 ${
                  isSelected
                    ? "border-emerald-400 ring-1 ring-emerald-400 bg-emerald-50/20"
                    : timeInfo.isExpired
                    ? "opacity-75 bg-slate-50"
                    : ""
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                        {req.line_item_category?.replace("-", " ") || "Trade Item"}
                      </span>
                      <span className="text-[11px] text-slate-500 font-medium">{req.boq_region}</span>
                    </div>
                    <h4 className="font-bold text-slate-900 text-sm leading-snug">
                      {req.line_item_description}
                    </h4>
                    <div className="text-xs text-slate-600">
                      Required Quantity: <strong className="text-slate-900 font-bold">{req.line_item_quantity} {req.line_item_unit}</strong>
                    </div>
                  </div>

                  {/* Outcome / Deadline Indicator */}
                  <div className="text-right whitespace-nowrap space-y-1">
                    {isSelected ? (
                      <span className="inline-block text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                        🏆 Winning Quote Selected
                      </span>
                    ) : (
                      <span
                        className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          timeInfo.isExpired
                            ? "bg-slate-200 text-slate-700"
                            : timeInfo.isUrgent
                            ? "bg-red-100 text-red-800 animate-pulse"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {timeInfo.text}
                      </span>
                    )}
                  </div>
                </div>

                {/* Status Footer */}
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  {myQuote ? (
                    <div className="text-emerald-700 font-bold font-mono flex items-center space-x-1.5">
                      <span>✓ Your Quote:</span>
                      <span>{formatZAR(myQuote.unit_price_minor)} / {req.line_item_unit}</span>
                      {myQuote.lead_time_days && (
                        <span className="text-[11px] text-slate-500 font-normal font-sans">
                          ({myQuote.lead_time_days} day lead time)
                        </span>
                      )}
                    </div>
                  ) : timeInfo.isExpired ? (
                    <span className="text-slate-400 font-medium">Deadline Passed</span>
                  ) : (
                    <span className="text-blue-600 font-bold flex items-center space-x-1">
                      <span>Tap to Submit Quote &rarr;</span>
                    </span>
                  )}
                  <span className="text-[11px] text-slate-400 font-mono">
                    Due: {formatDateTime(req.response_deadline)}
                  </span>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
