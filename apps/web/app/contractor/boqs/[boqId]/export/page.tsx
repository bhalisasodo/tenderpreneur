"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, AuditEventDTO, BoQComparisonDTO } from "@/lib/api";
import { formatDateTime, formatZAR } from "@/lib/formatters";

export default function ExportPage() {
  const params = useParams();
  const boqId = (params?.boqId as string) || "";

  const [data, setData] = useState<BoQComparisonDTO | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEventDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportingFmt, setExportingFmt] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getQuoteComparison(boqId),
      api.getAuditTrail(boqId),
    ]).then(([comp, audit]) => {
      setData(comp);
      setAuditEvents(audit);
      setLoading(false);
    }).catch((err) => {
      alert("Failed to load export data: " + err.message);
      setLoading(false);
    });
  }, [boqId]);

  const handleDownload = async (format: "xlsx" | "pdf") => {
    try {
      setExportingFmt(format);
      const res = await api.createExport(boqId, format);
      // Trigger browser download via API endpoint
      window.location.href = `http://localhost:8000${res.download_url}`;
    } catch (err: any) {
      alert("Export failed: " + err.message);
    } finally {
      setExportingFmt(null);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-sm text-slate-500">Loading export preview and audit trail...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center text-sm text-red-600 bg-red-50">BoQ data not found</div>;
  }

  const unpricedCount = data.line_items.filter((i) => !i.final_price_minor).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs text-slate-500 font-medium mb-1">
              <span>Tender Ref: <strong className="text-slate-800">{data.title}</strong></span>
              <span>&bull;</span>
              <span>Region: <strong className="text-slate-800">{data.region}</strong></span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Submission-Ready Priced BoQ &amp; Audit Trail</h1>
          </div>

          <div className="flex items-center space-x-2">
            <a
              href={`/contractor/boqs/${data.boq_id}/quotes`}
              className="px-3.5 py-1.5 rounded-lg text-slate-600 hover:bg-slate-50 font-semibold text-xs border border-slate-200"
            >
              &larr; 2. Compare Quotes
            </a>
            <a
              href={`/contractor/boqs/${data.boq_id}/export`}
              className="px-3.5 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 font-bold text-xs border border-emerald-200"
            >
              3. Export Priced BoQ
            </a>
          </div>
        </div>

        {unpricedCount > 0 && (
          <div className="mt-4 p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 font-medium">
            ⚠️ Notice: <strong>{unpricedCount}</strong> line item(s) are not yet priced. You can still export a draft schedule or return to the quotes tab to select prices.
          </div>
        )}
      </div>

      {/* Export Action Card */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-blue-900 text-blue-300 border border-blue-700">
            Tender Package Export
          </span>
          <h3 className="text-xl font-bold">Download Verified Priced Schedule</h3>
          <p className="text-xs text-slate-400 max-w-lg">
            Includes all itemized final rates, contractor selections, supplier quote references, and an immutable audit trail sheet for procurement defense.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={() => handleDownload("xlsx")}
            disabled={exportingFmt !== null}
            className="w-full sm:w-auto px-5 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md transition flex items-center justify-center space-x-2"
          >
            <span>📊</span>
            <span>{exportingFmt === "xlsx" ? "Generating..." : "Download Excel (.xlsx)"}</span>
          </button>
          <button
            onClick={() => handleDownload("pdf")}
            disabled={exportingFmt !== null}
            className="w-full sm:w-auto px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md transition flex items-center justify-center space-x-2"
          >
            <span>📑</span>
            <span>{exportingFmt === "pdf" ? "Generating..." : "Download PDF (.pdf)"}</span>
          </button>
        </div>
      </div>

      {/* Priced BoQ Table Preview */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Priced Schedule Schedule Overview</h3>
            <p className="text-xs text-slate-500">Live preview of the exported tender document.</p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-500">Grand Total Tender Price:</span>
            <div className="text-lg font-black text-emerald-700 font-mono">
              {formatZAR(data.total_priced_minor)}
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-3 px-4 w-12">#</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Unit</th>
                <th className="py-3 px-4 text-right">Qty</th>
                <th className="py-3 px-4 text-right">Rate (ZAR)</th>
                <th className="py-3 px-4 text-right">Total (ZAR)</th>
                <th className="py-3 px-4">Pricing Evidence / Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {data.line_items.map((item, idx) => {
                const qty = item.quantity;
                const unitRate = item.final_price_minor ? item.final_price_minor / 100 : 0;
                const total = unitRate * qty;
                const selectedQuote = item.selected_quote;

                return (
                  <tr key={item.line_item_id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 text-slate-400 font-sans">{idx + 1}</td>
                    <td className="py-3 px-4 font-sans font-medium text-slate-900">{item.description}</td>
                    <td className="py-3 px-4 font-sans capitalize text-slate-600">{item.category.replace("-", " ")}</td>
                    <td className="py-3 px-4 font-sans text-slate-600">{item.unit}</td>
                    <td className="py-3 px-4 text-right font-medium">{qty.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right font-semibold text-slate-900">
                      {item.final_price_minor ? formatZAR(item.final_price_minor) : "—"}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-emerald-700">
                      {item.final_price_minor ? formatZAR(Math.round(total * 100)) : "—"}
                    </td>
                    <td className="py-3 px-4 font-sans text-[11px]">
                      {selectedQuote ? (
                        <span className="text-emerald-700 font-semibold">
                          Quote #{selectedQuote.id.slice(0, 8)} ({selectedQuote.supplier_name})
                        </span>
                      ) : item.pricing_status === "manually_priced" ? (
                        <span className="text-blue-700 font-semibold">Manual Contractor Override</span>
                      ) : (
                        <span className="text-slate-400">Unpriced</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-slate-100 border-t-2 border-slate-300 font-mono">
              <tr>
                <td colSpan={6} className="py-3.5 px-4 text-right font-sans font-bold text-slate-900 text-sm">
                  TOTAL TENDER AMOUNT (ZAR):
                </td>
                <td className="py-3.5 px-4 text-right font-extrabold text-emerald-700 text-sm">
                  {formatZAR(data.total_priced_minor)}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Audit Trail Timeline */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Immutable Pricing Audit Trail</h3>
            <p className="text-xs text-slate-500">
              Traceable log of all material actions, quote selections, and price overrides for this tender.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700">
            {auditEvents.length} Recorded Events
          </span>
        </div>

        <div className="space-y-3">
          {auditEvents.map((event) => (
            <div
              key={event.id}
              className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[10px] uppercase">
                    {event.action}
                  </span>
                  <span className="font-semibold text-slate-800">
                    {event.actor_name || "System"}
                  </span>
                </div>
                <div className="text-slate-600 font-mono text-[11px]">
                  {event.after_json ? JSON.stringify(event.after_json) : "—"}
                </div>
              </div>

              <div className="text-[11px] text-slate-500 whitespace-nowrap">
                {formatDateTime(event.created_at)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
