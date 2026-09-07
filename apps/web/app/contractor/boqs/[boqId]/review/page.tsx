"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api, BoQDetailDTO, LineItemDTO } from "@/lib/api";
import { formatZAR } from "@/lib/formatters";

const CATEGORY_ICONS: Record<string, string> = {
  "building-materials": "🧱",
  "concrete": "🏗️",
  "earthworks": "🚜",
  "roofing": "🏠",
  "plumbing": "🚰",
  "electrical": "⚡",
  "finishes": "🎨",
  "ppe": "🦺",
  "plant-hire": "🚚",
  "general-building": "📋",
};

function checkIsCorrupted(text: string): { isCorrupted: boolean; reason?: string } {
  if (!text) return { isCorrupted: false };
  if (text.includes("\ufffd")) {
    return { isCorrupted: true, reason: "Contains Unicode replacement characters (garbled binary/encoding)" };
  }
  if (text.includes("\x00")) {
    return { isCorrupted: true, reason: "Contains null bytes (raw binary corruption)" };
  }
  if (/cid:\d+/i.test(text) || text.includes("(cid:")) {
    return { isCorrupted: true, reason: "Contains unmapped PDF font CID characters" };
  }
  if (text.includes("PK\x03\x04") || text.includes("PK\u0003\u0004")) {
    return { isCorrupted: true, reason: "Contains raw zip/xlsx archive headers" };
  }
  const clean = text.trim();
  if (clean.length > 5) {
    let unprintableCount = 0;
    for (let i = 0; i < clean.length; i++) {
      const code = clean.charCodeAt(i);
      if (code < 32 && code !== 9 && code !== 10 && code !== 13) {
        unprintableCount++;
      }
    }
    if (unprintableCount / clean.length > 0.05) {
      return { isCorrupted: true, reason: "High density of unprintable control characters" };
    }
  }
  return { isCorrupted: false };
}

export default function BoQReviewPage() {
  const params = useParams();
  const boqId = (params?.boqId as string) || "";
  const router = useRouter();

  const [boq, setBoq] = useState<BoQDetailDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(new Set());
  
  // Review Status Tab: "needs_review" | "accepted" | "excluded" | "all"
  const [reviewTab, setReviewTab] = useState<"needs_review" | "accepted" | "excluded" | "all">("needs_review");
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string>("all");
  
  const [deadlineHours, setDeadlineHours] = useState(48);
  const [broadcasting, setBroadcasting] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [broadcastSuccess, setBroadcastSuccess] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Edit Line Item Modal State
  const [editingItem, setEditingItem] = useState<LineItemDTO | null>(null);
  const [editForm, setEditForm] = useState({
    description: "",
    unit: "no",
    quantity: 1,
    category: "general-building",
  });
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    loadBoQ();
  }, [boqId]);

  const loadBoQ = async () => {
    try {
      setLoading(true);
      const data = await api.getBoQ(boqId);
      setBoq(data);

      const needsRev = data.line_items.filter((i) => i.review_status === "needs_review").length;
      if (needsRev === 0) {
        setReviewTab("accepted");
      } else {
        setReviewTab("needs_review");
      }

      // Default select all active accepted items for broadcast
      const acceptedIds = new Set(
        data.line_items
          .filter((i) => i.review_status !== "excluded" && i.quantity > 0 && i.pricing_status === "unsourced")
          .map((i) => i.id)
      );
      setSelectedItemIds(acceptedIds);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selectedItemIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedItemIds(next);
  };

  // Filter items based on review tab and category
  const filteredItems = (boq?.line_items || []).filter((item) => {
    // Review Tab Filter
    if (reviewTab === "needs_review" && item.review_status !== "needs_review") return false;
    if (reviewTab === "accepted" && item.review_status !== "accepted") return false;
    if (reviewTab === "excluded" && item.review_status !== "excluded") return false;

    // Category Filter
    if (activeCategoryFilter !== "all" && item.category !== activeCategoryFilter) return false;

    return true;
  });

  const selectAllFiltered = () => {
    const next = new Set(selectedItemIds);
    filteredItems.forEach((i) => {
      if (i.review_status !== "excluded") next.add(i.id);
    });
    setSelectedItemIds(next);
  };

  const deselectAllFiltered = () => {
    const next = new Set(selectedItemIds);
    filteredItems.forEach((i) => next.delete(i.id));
    setSelectedItemIds(next);
  };

  const selectAcceptedOnly = () => {
    if (!boq) return;
    const accepted = boq.line_items.filter((i) => i.review_status === "accepted" && i.quantity > 0);
    setSelectedItemIds(new Set(accepted.map((i) => i.id)));
  };

  const handleConfirmItem = async (item: LineItemDTO) => {
    if (!boq) return;
    try {
      const updated = await api.updateLineItem(boq.id, item.id, { review_status: "accepted" });
      setBoq({
        ...boq,
        line_items: boq.line_items.map((i) => (i.id === updated.id ? updated : i)),
      });
      const next = new Set(selectedItemIds);
      next.add(item.id);
      setSelectedItemIds(next);
      setActionNotice(`✓ Confirmed item: "${item.description.slice(0, 40)}..."`);
    } catch (err: any) {
      alert("Failed to confirm item: " + err.message);
    }
  };

  const handleRestoreItem = async (item: LineItemDTO) => {
    if (!boq) return;
    try {
      const updated = await api.restoreLineItem(boq.id, item.id);
      setBoq({
        ...boq,
        line_items: boq.line_items.map((i) => (i.id === updated.id ? updated : i)),
      });
      const next = new Set(selectedItemIds);
      next.add(item.id);
      setSelectedItemIds(next);
      setActionNotice(`✓ Restored item to active queue: "${item.description.slice(0, 40)}..."`);
    } catch (err: any) {
      alert("Failed to restore item: " + err.message);
    }
  };

  const openEditModal = (item: LineItemDTO) => {
    setEditingItem(item);
    setEditForm({
      description: item.description,
      unit: item.unit,
      quantity: item.quantity,
      category: item.category,
    });
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !boq) return;
    try {
      setSavingEdit(true);
      const updated = await api.updateLineItem(boq.id, editingItem.id, {
        ...editForm,
        review_status: "accepted", // mark as confirmed on edit
      });
      setBoq({
        ...boq,
        line_items: boq.line_items.map((i) => (i.id === updated.id ? updated : i)),
      });
      setEditingItem(null);
      setActionNotice(`✓ Saved correction for: "${updated.description.slice(0, 40)}..."`);
    } catch (err: any) {
      alert("Failed to save correction: " + err.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!boq || !confirm("Exclude/Delete this line item?")) return;
    try {
      await api.deleteLineItem(boq.id, itemId);
      setBoq({
        ...boq,
        line_items: boq.line_items.filter((i) => i.id !== itemId),
      });
      const next = new Set(selectedItemIds);
      next.delete(itemId);
      setSelectedItemIds(next);
    } catch (err: any) {
      alert("Failed to delete: " + err.message);
    }
  };

  const handleBulkDelete = async () => {
    if (!boq || selectedItemIds.size === 0) return;
    const count = selectedItemIds.size;
    if (!confirm(`Are you sure you want to remove ${count} selected line item(s) from this BoQ?`)) return;

    try {
      setBulkDeleting(true);
      const idsToDelete = Array.from(selectedItemIds);
      await api.bulkDeleteLineItems(boq.id, idsToDelete);

      setBoq({
        ...boq,
        line_items: boq.line_items.filter((i) => !selectedItemIds.has(i.id)),
      });
      setSelectedItemIds(new Set());
    } catch (err: any) {
      alert("Bulk delete failed: " + err.message);
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleBroadcast = async () => {
    if (!boq || selectedItemIds.size === 0) return;
    try {
      setBroadcasting(true);
      setBroadcastSuccess(null);

      // Pre-broadcast safety gate check
      const validation = await api.validateBroadcastSafety(boq.id, Array.from(selectedItemIds));
      const isSafe = validation.safe !== undefined ? validation.safe : validation.is_safe;
      if (!isSafe) {
        const issues = validation.corrupted_items.map((i) => `• ${i.description.slice(0, 30)}: ${i.reason}`).join("\n");
        alert(`Broadcast blocked by Pre-Broadcast Safety Gate:\n\n${validation.message}\n\n${issues}`);
        return;
      }

      const deadline = new Date(Date.now() + deadlineHours * 60 * 60 * 1000).toISOString();
      let successCount = 0;

      for (const itemId of Array.from(selectedItemIds)) {
        const qr = await api.createQuoteRequest(itemId, deadline);
        await api.broadcastQuoteRequest(qr.id);
        successCount++;
      }

      setBroadcastSuccess(`Successfully broadcast quote requests for ${successCount} line items!`);
      setTimeout(() => {
        router.push(`/contractor/boqs/${boq.id}/quotes`);
      }, 1200);
    } catch (err: any) {
      alert("Broadcast failed: " + err.message);
    } finally {
      setBroadcasting(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-sm text-slate-500">Loading BoQ details...</div>;
  }

  if (error || !boq) {
    return <div className="p-8 text-center text-sm text-red-600 bg-red-50">{error || "BoQ not found"}</div>;
  }

  // Pre-Broadcast Safety Gate: detect corrupted text in line items
  const corruptedItemsMap = new Map<string, string>();
  boq.line_items.forEach((item) => {
    const res = checkIsCorrupted(item.description);
    if (res.isCorrupted && res.reason) {
      corruptedItemsMap.set(item.id, res.reason);
    }
  });

  const corruptedSelectedCount = Array.from(selectedItemIds).filter((id) =>
    corruptedItemsMap.has(id)
  ).length;
  const hasCorruptedSelected = corruptedSelectedCount > 0;

  // Count review metrics
  const needsReviewCount = boq.line_items.filter((i) => i.review_status === "needs_review").length;
  const acceptedCount = boq.line_items.filter((i) => i.review_status === "accepted").length;
  const excludedCount = boq.line_items.filter((i) => i.review_status === "excluded").length;

  // Count categories across active items
  const categoryCounts: Record<string, number> = {};
  boq.line_items.forEach((item) => {
    categoryCounts[item.category] = (categoryCounts[item.category] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      {/* BoQ Header & Navigation Tabs */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs text-slate-500 font-medium mb-1">
              <span>Tender Ref: <strong className="text-slate-800">{boq.tender_reference || "N/A"}</strong></span>
              <span>&bull;</span>
              <span>Region: <strong className="text-slate-800">{boq.region}</strong></span>
              <span>&bull;</span>
              <span>Total Parsed: <strong className="text-slate-800">{boq.line_items.length}</strong></span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">{boq.title}</h1>
          </div>

          <div className="flex items-center space-x-2">
            <Link
              href={`/contractor/boqs/${boq.id}/review`}
              className="px-3.5 py-1.5 rounded-lg bg-blue-50 text-blue-700 font-bold text-xs border border-blue-200"
            >
              1. Review &amp; Source
            </Link>
            <Link
              href={`/contractor/boqs/${boq.id}/quotes`}
              className="px-3.5 py-1.5 rounded-lg text-slate-600 hover:bg-slate-50 font-semibold text-xs border border-slate-200"
            >
              2. Compare Quotes &rarr;
            </Link>
            <Link
              href={`/contractor/boqs/${boq.id}/export`}
              className="px-3.5 py-1.5 rounded-lg text-slate-600 hover:bg-slate-50 font-semibold text-xs border border-slate-200"
            >
              3. Export Priced BoQ &rarr;
            </Link>
          </div>
        </div>
      </div>

      {actionNotice && (
        <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-900 font-bold flex items-center justify-between">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-blue-500 hover:text-blue-800 font-bold">&times;</button>
        </div>
      )}

      {broadcastSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-bold">
          {broadcastSuccess} Navigating to quotes comparison...
        </div>
      )}

      {/* Parser Accuracy & Human Review Queue Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button
          onClick={() => setReviewTab("needs_review")}
          className={`p-4 rounded-2xl border text-left transition ${
            reviewTab === "needs_review"
              ? "bg-amber-50/80 border-amber-400 ring-2 ring-amber-400/20 shadow-sm"
              : "bg-white border-slate-200 hover:bg-slate-50"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-800 uppercase tracking-wider">⚠️ Needs Human Review</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-200 text-amber-900 font-bold">
              {needsReviewCount}
            </span>
          </div>
          <div className="text-xl font-extrabold text-amber-900 mt-1">{needsReviewCount} Ambiguous Items</div>
          <div className="text-[11px] text-amber-700 mt-0.5">Uncertain units, quantities, or trade scopes</div>
        </button>

        <button
          onClick={() => setReviewTab("accepted")}
          className={`p-4 rounded-2xl border text-left transition ${
            reviewTab === "accepted"
              ? "bg-emerald-50/80 border-emerald-400 ring-2 ring-emerald-400/20 shadow-sm"
              : "bg-white border-slate-200 hover:bg-slate-50"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider">✓ Auto-Accepted</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-200 text-emerald-900 font-bold">
              {acceptedCount}
            </span>
          </div>
          <div className="text-xl font-extrabold text-emerald-900 mt-1">{acceptedCount} High Confidence</div>
          <div className="text-[11px] text-emerald-700 mt-0.5">Confirmed BoQ items ready for RFQ broadcast</div>
        </button>

        <button
          onClick={() => setReviewTab("excluded")}
          className={`p-4 rounded-2xl border text-left transition ${
            reviewTab === "excluded"
              ? "bg-slate-100 border-slate-400 ring-2 ring-slate-400/20 shadow-sm"
              : "bg-white border-slate-200 hover:bg-slate-50"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">🚫 Excluded Non-Items</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-800 font-bold">
              {excludedCount}
            </span>
          </div>
          <div className="text-xl font-extrabold text-slate-800 mt-1">{excludedCount} Filtered Clauses</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Legal text, headers, and subtotals omitted</div>
        </button>
      </div>

      {/* Pre-Broadcast Safety Gate Alert */}
      {hasCorruptedSelected && (
        <div className="p-4 rounded-2xl bg-rose-50 border-2 border-rose-300 text-rose-950 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start space-x-3">
            <span className="text-2xl mt-0.5">🛑</span>
            <div>
              <h4 className="font-extrabold text-sm text-rose-900">
                Pre-Broadcast Safety Gate Active ({corruptedSelectedCount} Corrupted Item{corruptedSelectedCount > 1 ? "s" : ""})
              </h4>
              <p className="text-xs text-rose-800 mt-0.5">
                Market broadcast to real suppliers is blocked because {corruptedSelectedCount} selected line item{corruptedSelectedCount > 1 ? "s contain" : " contains"} garbled or unreadable text (replacement characters, null bytes, or binary noise). Please edit or exclude them before dispatching RFQs.
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              const next = new Set(selectedItemIds);
              for (const [id] of corruptedItemsMap.entries()) {
                next.delete(id);
              }
              setSelectedItemIds(next);
            }}
            className="px-3.5 py-1.5 rounded-lg bg-rose-700 hover:bg-rose-800 text-white font-bold text-xs shadow-sm transition whitespace-nowrap"
          >
            Deselect Corrupted Items
          </button>
        </div>
      )}

      {/* Broadcast Action Panel */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white rounded-2xl p-6 shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="text-xs font-bold uppercase tracking-wider text-blue-300">Supplier Quote Sourcing</div>
          <h3 className="text-lg font-bold">Broadcast Confirmed Items to Matched Suppliers</h3>
          <p className="text-xs text-blue-200">
            {selectedItemIds.size} of {acceptedCount} active items selected for market quote sourcing in {boq.region}.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 text-xs">
            <label className="font-semibold text-blue-200">Response Window:</label>
            <select
              value={deadlineHours}
              onChange={(e) => setDeadlineHours(Number(e.target.value))}
              className="bg-blue-950/80 border border-blue-700 text-white rounded-lg px-2.5 py-2 text-xs font-semibold focus:outline-none"
            >
              <option value={24}>24 Hours (Urgent)</option>
              <option value={48}>48 Hours (Standard)</option>
              <option value={72}>72 Hours (3 Days)</option>
              <option value={120}>5 Days</option>
            </select>
          </div>

          <button
            onClick={handleBroadcast}
            disabled={broadcasting || selectedItemIds.size === 0 || hasCorruptedSelected}
            className={`px-5 py-2.5 rounded-xl text-white text-xs font-bold shadow-lg transition flex items-center space-x-2 ${
              hasCorruptedSelected
                ? "bg-rose-700 hover:bg-rose-800 cursor-not-allowed opacity-90"
                : "bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
            }`}
          >
            {broadcasting ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Broadcasting Requests...</span>
              </>
            ) : hasCorruptedSelected ? (
              <>
                <span>🚫 Broadcast Blocked ({corruptedSelectedCount} Corrupted)</span>
              </>
            ) : (
              <>
                <span>📡 Broadcast Quote Requests ({selectedItemIds.size})</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Smart Filters & Bulk Tools Bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
        {/* Category Filter Chips */}
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 pb-3">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mr-1">Filter Trade:</span>
          <button
            onClick={() => setActiveCategoryFilter("all")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
              activeCategoryFilter === "all"
                ? "bg-slate-900 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            All Trades ({boq.line_items.length})
          </button>
          {Object.entries(categoryCounts).map(([cat, count]) => {
            const isSelected = activeCategoryFilter === cat;
            const icon = CATEGORY_ICONS[cat] || "📋";
            return (
              <button
                key={cat}
                onClick={() => setActiveCategoryFilter(cat)}
                className={`px-3 py-1 rounded-full text-xs font-semibold capitalize transition flex items-center space-x-1.5 ${
                  isSelected
                    ? "bg-blue-600 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                <span>{icon}</span>
                <span>{cat.replace("-", " ")}</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${isSelected ? "bg-blue-800 text-white" : "bg-slate-200 text-slate-700"}`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Quick Selection Presets & Bulk Actions */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex items-center space-x-2 text-xs">
            <span className="font-semibold text-slate-700">Quick Selection:</span>
            <button
              onClick={selectAcceptedOnly}
              className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200 hover:bg-emerald-100 transition text-xs"
            >
              ✓ Select Confirmed Items Only
            </button>
            <button
              onClick={selectAllFiltered}
              className="px-2.5 py-1 rounded-lg bg-slate-50 text-slate-700 font-medium border border-slate-200 hover:bg-slate-100 transition text-xs"
            >
              Select All in View
            </button>
            <button
              onClick={deselectAllFiltered}
              className="px-2.5 py-1 rounded-lg text-slate-500 hover:text-slate-800 transition text-xs"
            >
              Deselect All
            </button>
          </div>

          {selectedItemIds.size > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-500 font-medium">
                {selectedItemIds.size} item(s) selected
              </span>
              <button
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
                className="px-3 py-1 rounded-lg bg-red-50 text-red-700 border border-red-200 font-semibold hover:bg-red-100 transition text-xs flex items-center space-x-1"
              >
                <span>🗑️</span>
                <span>{bulkDeleting ? "Removing..." : `Exclude Selected (${selectedItemIds.size})`}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Line Items Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {filteredItems.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500 space-y-1">
            <div className="text-2xl">✓</div>
            <div className="font-bold text-slate-700">No Items in this Review Queue</div>
            <p>
              {reviewTab === "needs_review"
                ? "All items have been reviewed or auto-accepted!"
                : "No items match the current filters."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4 w-10">
                    <input
                      type="checkbox"
                      checked={filteredItems.length > 0 && filteredItems.every((i) => selectedItemIds.has(i.id))}
                      onChange={() => {
                        if (filteredItems.every((i) => selectedItemIds.has(i.id))) {
                          deselectAllFiltered();
                        } else {
                          selectAllFiltered();
                        }
                      }}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                  </th>
                  <th className="py-3 px-4 w-14">Ref</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4 w-36">Category</th>
                  <th className="py-3 px-4 w-20">Unit</th>
                  <th className="py-3 px-4 w-24 text-right">Quantity</th>
                  <th className="py-3 px-4 w-32 text-center">Confidence</th>
                  <th className="py-3 px-4 w-28 text-center">Review State</th>
                  <th className="py-3 px-4 w-36 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredItems.map((item) => {
                  const isSelected = selectedItemIds.has(item.id);
                  const icon = CATEGORY_ICONS[item.category] || "📋";
                  const isExcluded = item.review_status === "excluded";
                  const isNeedsReview = item.review_status === "needs_review";
                  const isCorrupted = corruptedItemsMap.has(item.id);
                  const corruptionReason = corruptedItemsMap.get(item.id);

                  return (
                    <tr
                      key={item.id}
                      className={`transition ${
                        isCorrupted
                          ? "bg-rose-50/70 hover:bg-rose-50/90"
                          : isSelected
                          ? "bg-blue-50/40"
                          : isNeedsReview
                          ? "bg-amber-50/30 hover:bg-amber-50/50"
                          : isExcluded
                          ? "opacity-60 bg-slate-50 hover:opacity-80"
                          : "hover:bg-slate-50"
                      }`}
                    >
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(item.id)}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-slate-700 text-[11px]">
                        {item.source_row_reference || "—"}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 leading-snug">{item.description}</div>
                        {isCorrupted && (
                          <div className="inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded mt-1 text-rose-800 bg-rose-100 border border-rose-300 space-x-1">
                            <span>🚫 Corrupted Text: {corruptionReason}</span>
                          </div>
                        )}
                        {item.exclusion_reason && !isCorrupted && (
                          <div className={`inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded mt-1 ${
                            isNeedsReview
                              ? "text-amber-800 bg-amber-100/80 border border-amber-200"
                              : "text-slate-600 bg-slate-100 border border-slate-200"
                          }`}>
                            <span>{isNeedsReview ? "⚠️ " : "🚫 "}{item.exclusion_reason}</span>
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700 capitalize">
                          <span>{icon}</span>
                          <span>{item.category.replace("-", " ")}</span>
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-slate-700">{item.unit}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                        {item.quantity.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {item.parsing_confidence !== undefined ? (
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                              item.parsing_confidence >= 0.80
                                ? "bg-emerald-100 text-emerald-800"
                                : item.parsing_confidence >= 0.50
                                ? "bg-amber-100 text-amber-800"
                                : "bg-red-100 text-red-800"
                            }`}
                          >
                            {(item.parsing_confidence * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            item.review_status === "accepted"
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                              : item.review_status === "needs_review"
                              ? "bg-amber-100 text-amber-800 border border-amber-300 animate-pulse"
                              : "bg-slate-200 text-slate-700"
                          }`}
                        >
                          {item.review_status?.replace("_", " ") || "accepted"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-1.5 whitespace-nowrap">
                        {isNeedsReview && (
                          <button
                            onClick={() => handleConfirmItem(item)}
                            className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] shadow-sm transition"
                          >
                            ✓ Confirm
                          </button>
                        )}
                        {isExcluded && (
                          <button
                            onClick={() => handleRestoreItem(item)}
                            className="px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] shadow-sm transition"
                          >
                            Restore
                          </button>
                        )}
                        <button
                          onClick={() => openEditModal(item)}
                          className="text-blue-600 hover:text-blue-800 font-semibold text-xs px-1"
                        >
                          Edit
                        </button>
                        {!isExcluded && (
                          <button
                            onClick={() => handleDeleteItem(item.id)}
                            className="text-red-500 hover:text-red-700 font-semibold text-xs px-1"
                          >
                            Exclude
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Manual Edit Line Item Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Correct BoQ Line Item</h3>
              <button
                onClick={() => setEditingItem(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Description</label>
                <textarea
                  rows={3}
                  required
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Trade Category</label>
                  <select
                    value={editForm.category}
                    onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                    className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
                  >
                    <option value="building-materials">🧱 Building Materials</option>
                    <option value="concrete">🏗️ Concrete</option>
                    <option value="earthworks">🚜 Earthworks</option>
                    <option value="roofing">🏠 Roofing</option>
                    <option value="plumbing">🚰 Plumbing</option>
                    <option value="electrical">⚡ Electrical</option>
                    <option value="finishes">🎨 Finishes</option>
                    <option value="ppe">🦺 PPE</option>
                    <option value="plant-hire">🚚 Plant Hire</option>
                    <option value="general-building">📋 General Building</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Unit of Measure</label>
                  <input
                    type="text"
                    required
                    value={editForm.unit}
                    onChange={(e) => setEditForm({ ...editForm, unit: e.target.value })}
                    className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Quantity</label>
                <input
                  type="number"
                  step="any"
                  required
                  value={editForm.quantity}
                  onChange={(e) => setEditForm({ ...editForm, quantity: Number(e.target.value) })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingEdit}
                  className="px-5 py-2 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 shadow"
                >
                  {savingEdit ? "Saving..." : "Save Correction & Confirm"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
