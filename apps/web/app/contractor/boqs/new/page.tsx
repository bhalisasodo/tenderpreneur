"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "../../../../lib/api";

export default function NewBoQPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [tenderRef, setTenderRef] = useState("");
  const [region, setRegion] = useState("KwaZulu-Natal");
  const [inputMode, setInputMode] = useState<"upload" | "paste">("upload");
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please provide a Tender Title.");
      return;
    }

    if (inputMode === "upload" && !file) {
      setError("Please select an Excel (.xlsx/.xls) or PDF BoQ file to upload.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      // 1. Create BoQ record
      const boq = await api.createBoQ({
        title: title.trim(),
        tender_reference: tenderRef.trim() || undefined,
        region,
      });

      // 2. Upload file or parse pasted text
      if (inputMode === "upload" && file) {
        await api.uploadBoQDocument(boq.id, file);
        await api.parseBoQ(boq.id);
      } else {
        await api.parseBoQ(boq.id, pastedText);
      }

      // 3. Navigate to review line items
      router.push(`/contractor/boqs/${boq.id}/review`);
    } catch (err: any) {
      setError(err.message || "Failed to create and parse BoQ");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Upload &amp; Ingest Tender BoQ</h2>
          <p className="text-xs text-slate-500">Provide tender details and upload a BoQ file or paste source text for extraction.</p>
        </div>
        <Link
          href="/contractor"
          className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg border border-slate-200"
        >
          Cancel
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
        {/* Section 1: Tender Metadata */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 border-b border-slate-100 pb-2">
            1. Tender Details
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Tender Title / Project Scope <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Durban High School New Admin Wing Renovation"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Tender Reference Code
              </label>
              <input
                type="text"
                placeholder="e.g. DOE-KZN-2026-092"
                value={tenderRef}
                onChange={(e) => setTenderRef(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Project Province / Region <span className="text-red-500">*</span>
              </label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="KwaZulu-Natal">KwaZulu-Natal</option>
                <option value="Gauteng">Gauteng</option>
                <option value="Western Cape">Western Cape</option>
                <option value="Eastern Cape">Eastern Cape</option>
                <option value="Free State">Free State</option>
                <option value="Mpumalanga">Mpumalanga</option>
                <option value="Limpopo">Limpopo</option>
                <option value="North West">North West</option>
                <option value="Northern Cape">Northern Cape</option>
              </select>
            </div>
          </div>
        </div>

        {/* Section 2: Ingestion Source */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
              2. BoQ Scope Ingestion
            </h3>
            <div className="flex rounded-lg bg-slate-100 p-0.5 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setInputMode("paste")}
                className={`px-3 py-1 rounded-md transition ${
                  inputMode === "paste" ? "bg-white text-blue-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Structured Text / Schedule
              </button>
              <button
                type="button"
                onClick={() => setInputMode("upload")}
                className={`px-3 py-1 rounded-md transition ${
                  inputMode === "upload" ? "bg-white text-blue-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Upload File (PDF/Excel)
              </button>
            </div>
          </div>

          {inputMode === "paste" ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700">
                  BoQ Schedule Data (Auto-categorized into Earthworks, Concrete, Masonry, Plumbing, Roofing)
                </label>
                <span className="text-[11px] text-slate-500">Automated schedule processing active</span>
              </div>
              <textarea
                rows={11}
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                placeholder="Paste tender bill of quantities, itemized schedules, or raw tables here..."
                className="w-full text-xs font-mono p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50"
              />
              <p className="text-[11px] text-slate-500">
                The system will automatically identify Bill sections, descriptions, units, quantities, trade categories, and benchmark pricing hints.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-blue-500 transition bg-slate-50">
                <div className="text-3xl mb-2">📄</div>
                <div className="text-xs font-semibold text-slate-800">
                  {file ? file.name : "Select Multi-Page BoQ Document (PDF, XLSX, XLS)"}
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  {file ? `${(file.size / 1024).toFixed(1)} KB (Ready to process)` : "Drag and drop or browse tender PDF / Excel schedule"}
                </div>
                <input
                  type="file"
                  accept=".pdf,.xlsx,.xls,.txt"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="mt-4 text-xs file:mr-3 file:py-1.5 file:px-3.5 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
                />
              </div>
            </div>
          )}
        </div>

        {/* Submit */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
          <div className="text-[11px] text-slate-500 font-medium">
            Step 1 of 3: Ingestion &rarr; 2. Line Item Review &rarr; 3. Marketplace Quotes
          </div>
          <div className="flex items-center space-x-3">
            <Link
              href="/contractor"
              className="px-4 py-2.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow transition flex items-center space-x-2 disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Processing Multi-Page BoQ...</span>
                </>
              ) : (
                <span>Create &amp; Process BoQ &rarr;</span>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
