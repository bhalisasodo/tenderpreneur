"use client";

import { useEffect, useState } from "react";
import { api, SupplierReviewDTO } from "../../../lib/api";

export default function SupplierReviewPage() {
  const [suppliers, setSuppliers] = useState<SupplierReviewDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);

  const loadQueue = async () => {
    try {
      setLoading(true);
      setSuppliers(await api.listSupplierReviewQueue());
      setError(null);
    } catch (queueError: any) {
      setError(queueError.message || "Could not load supplier review queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const updateStatus = async (supplier: SupplierReviewDTO, action: "approve" | "suspend") => {
    const reason = window.prompt(action === "approve" ? "Approval note" : "Suspension reason");
    if (reason === null) return;
    try {
      setWorkingId(supplier.organisation_id);
      if (action === "approve") {
        await api.approveSupplier(supplier.organisation_id, reason);
      } else {
        await api.suspendSupplier(supplier.organisation_id, reason);
      }
      await loadQueue();
    } catch (statusError: any) {
      setError(statusError.message || "Could not update supplier status.");
    } finally {
      setWorkingId(null);
    }
  };

  return (
    <main className="max-w-6xl mx-auto space-y-6">
      <header>
        <p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Platform operations</p>
        <h1 className="mt-2 text-3xl font-serif font-bold text-[#12233F]">Durban supplier review</h1>
        <p className="mt-2 text-sm text-slate-600">Approve or suspend suppliers before they enter the KwaZulu-Natal quote pool.</p>
      </header>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">Loading review queue...</div>
      ) : suppliers.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">No suppliers currently require review.</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Supplier</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Categories</th>
                <th className="px-4 py-3">Coverage</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {suppliers.map((supplier) => (
                <tr key={supplier.organisation_id}>
                  <td className="px-4 py-4 font-semibold text-slate-900">{supplier.legal_name}</td>
                  <td className="px-4 py-4 text-slate-600">{supplier.email}<br />{supplier.phone || "No phone"}</td>
                  <td className="px-4 py-4 text-slate-600">{supplier.categories.join(", ") || "Not set"}</td>
                  <td className="px-4 py-4 text-slate-600">{supplier.service_regions.join(", ") || supplier.region}</td>
                  <td className="px-4 py-4"><span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">{supplier.approval_status}</span></td>
                  <td className="px-4 py-4 text-right whitespace-nowrap">
                    <button disabled={workingId === supplier.organisation_id} onClick={() => updateStatus(supplier, "approve")} className="mr-2 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Approve</button>
                    <button disabled={workingId === supplier.organisation_id} onClick={() => updateStatus(supplier, "suspend")} className="rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 disabled:opacity-50">Suspend</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
