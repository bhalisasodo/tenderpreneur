"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, BoQSummaryDTO } from "../../lib/api";
import { formatDateTime, formatZAR } from "../../lib/formatters";

export default function ContractorDashboard() {
  const [boqs, setBoqs] = useState<BoQSummaryDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Deletion state
  const [boqToDelete, setBoqToDelete] = useState<BoQSummaryDTO | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  useEffect(() => {
    loadBoQs();
  }, []);

  const loadBoQs = async () => {
    try {
      setLoading(true);
      const data = await api.listBoQs();
      setBoqs(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!boqToDelete) return;
    try {
      setDeletingId(boqToDelete.id);
      setDeleteError(null);
      await api.deleteBoQ(boqToDelete.id);
      setBoqs((prev) => prev.filter((b) => b.id !== boqToDelete.id));
      setSuccessNotice(`Tender BoQ "${boqToDelete.title}" was successfully deleted.`);
      setBoqToDelete(null);
    } catch (err: any) {
      setDeleteError(err.message || "Failed to delete BoQ. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "draft":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">Draft Document</span>;
      case "parsed":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700">Parsed &amp; Review</span>;
      case "in_sourcing":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">Quotes In Progress</span>;
      case "priced":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">Priced &amp; Ready</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Success Notification */}
      {successNotice && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-emerald-600 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">{successNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessNotice(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-4 text-base leading-none"
            aria-label="Dismiss notice"
          >
            &times;
          </button>
        </div>
      )}

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Tender BoQs</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{boqs.length}</div>
          <div className="text-xs text-slate-500 mt-1">Estimates in progress</div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Line Items Tracked</div>
          <div className="text-2xl font-bold text-blue-600 mt-1">
            {boqs.reduce((acc, b) => acc + (b.line_item_count || 0), 0)}
          </div>
          <div className="text-xs text-slate-500 mt-1">Across all tender scopes</div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Priced BoQ Sum</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">
            {formatZAR(boqs.reduce((acc, b) => acc + (b.total_priced_minor || 0), 0))}
          </div>
          <div className="text-xs text-slate-500 mt-1">Validated pricing with quote audit</div>
        </div>
      </div>

      {/* BoQ List Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Your Tender BoQs</h3>
            <p className="text-xs text-slate-500">Click a tender to view line items, source quotes, or generate exports.</p>
          </div>
          <button
            onClick={loadBoQs}
            className="text-xs text-slate-500 hover:text-slate-800 font-medium px-2.5 py-1 rounded border border-slate-200 hover:bg-slate-50"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-sm text-slate-500">Loading tender BoQs...</div>
        ) : error ? (
          <div className="p-8 text-center text-sm text-red-600 bg-red-50">{error}</div>
        ) : boqs.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="text-3xl">📄</div>
            <h4 className="font-bold text-slate-800">No BoQs Created Yet</h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Upload your tender document (PDF, Excel, or scope text) to begin parsing line items and sourcing verified supplier quotes.
            </p>
            <Link
              href="/contractor/boqs/new"
              className="inline-block mt-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow transition"
            >
              Upload Your First BoQ &rarr;
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Tender Reference / Title</th>
                  <th className="py-3 px-4">Region</th>
                  <th className="py-3 px-4">Items</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Priced Total (ZAR)</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {boqs.map((boq) => (
                  <tr key={boq.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900 text-sm">{boq.title}</div>
                      <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                        {boq.tender_reference ? `Ref: ${boq.tender_reference}` : "No Ref"} &bull; Created {formatDateTime(boq.created_at)}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-700">{boq.region}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">{boq.line_item_count} items</td>
                    <td className="py-3.5 px-4">{getStatusBadge(boq.status)}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      {boq.total_priced_minor > 0 ? (
                        <span className="text-emerald-700">{formatZAR(boq.total_priced_minor)}</span>
                      ) : (
                        <span className="text-slate-400 font-normal">Unpriced</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                      <Link
                        href={`/contractor/boqs/${boq.id}/review`}
                        className="px-2.5 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition"
                      >
                        Review Items
                      </Link>
                      <Link
                        href={`/contractor/boqs/${boq.id}/quotes`}
                        className="px-2.5 py-1.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold text-xs transition"
                      >
                        Compare Quotes
                      </Link>
                      <Link
                        href={`/contractor/boqs/${boq.id}/export`}
                        className="px-2.5 py-1.5 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-semibold text-xs transition"
                      >
                        Export
                      </Link>
                      <button
                        type="button"
                        onClick={() => {
                          setBoqToDelete(boq);
                          setDeleteError(null);
                        }}
                        className="px-2.5 py-1.5 rounded bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold text-xs transition border border-rose-200/60 inline-flex items-center gap-1"
                        title="Delete BoQ"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {boqToDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
        >
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center shrink-0">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </div>
              <div>
                <h3
                  id="delete-modal-title"
                  className="font-bold text-slate-900 text-base"
                >
                  Delete Tender BoQ
                </h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  Are you sure you want to permanently delete{" "}
                  <span className="font-semibold text-slate-900">
                    &ldquo;{boqToDelete.title}&rdquo;
                  </span>
                  {boqToDelete.tender_reference
                    ? ` (Ref: ${boqToDelete.tender_reference})`
                    : ""}
                  ?
                </p>
              </div>
            </div>

            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800 leading-relaxed">
              <strong>Warning:</strong> This will permanently delete this BoQ
              estimate, all {boqToDelete.line_item_count} line items, uploaded
              source files, and associated quote requests. This action cannot be undone.
            </div>

            {deleteError && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700">
                {deleteError}
              </div>
            )}

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                disabled={deletingId !== null}
                onClick={() => {
                  setBoqToDelete(null);
                  setDeleteError(null);
                }}
                className="px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deletingId !== null}
                onClick={handleConfirmDelete}
                className="px-3.5 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-sm transition disabled:opacity-50 inline-flex items-center gap-1.5"
              >
                {deletingId ? (
                  <>
                    <svg
                      className="animate-spin h-3.5 w-3.5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v8H4z"
                      ></path>
                    </svg>
                    Deleting...
                  </>
                ) : (
                  "Delete BoQ"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
