"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../../../lib/api";

interface TenderPreset {
  id: string;
  name: string;
  badge: string;
  title: string;
  ref: string;
  region: string;
  scheduleText: string;
}

const TENDER_PRESETS: TenderPreset[] = [
  {
    id: "ethekwini-water",
    name: "eThekwini Water & Sanitation",
    badge: "Durban, KZN (Civils)",
    title: "eThekwini Municipality - Bulk Water Pipeline & Earthworks Upgrade",
    ref: "WS-7840/2026",
    region: "KwaZulu-Natal",
    scheduleText: `Bill No. 1: Earthworks & Site Clearance
1.01 | Clear and strip site of vegetation and topsoil | 1200.0 | m2
1.02 | Excavation in soft earth for pipe trenches not exceeding 2.5m | 650.0 | m3
1.03 | Selected granular bedding and backfilling compacted to 93% Mod AASHTO | 420.0 | m3

Bill No. 2: Concrete, Formwork & Reinforcement
2.01 | Mass concrete 15MPa for pipe anchor blocks and thrust cradles | 85.0 | m3
2.02 | Reinforced 30MPa ready-mix concrete in valve inspection chambers | 140.0 | m3
2.03 | High tensile deformed steel reinforcement rebar | 12.0 | ton

Bill No. 3: Pipework & Protection
3.01 | 300mm Class 16 uPVC bulk pressure water pipeline with rubber rings | 850.0 | m
3.02 | 300mm double flange cast iron gate valves with handwheels | 6.0 | no
3.03 | Personal Protective Equipment (PPE) site sets: hardhats, vests, boots | 30.0 | no`,
  },
  {
    id: "gauteng-did",
    name: "Gauteng DID Clinic Upgrade",
    badge: "Joburg/Pretoria, GP (Building)",
    title: "Gauteng Dept of Infrastructure - Mamelodi Clinic Ward Renovation",
    ref: "DID-GP-2026-114",
    region: "Gauteng",
    scheduleText: `Bill No. 1: Demolition & Site Preparation
1.01 | Break down and remove internal brick partition walls | 220.0 | m2
1.02 | Excavate foundation trenches for new outpatient consulting wing | 180.0 | m3

Bill No. 2: Masonry & Superstructure
2.01 | Standard clay stock bricks (NFP) in 1:4 cement mortar for walls | 28000.0 | no
2.02 | 50kg All-Purpose Portland Cement CEM II 42.5N bags | 450.0 | no
2.03 | 25MPa ready-mix concrete for floor slabs and surface beds | 95.0 | m3

Bill No. 3: Finishes & Electrical
3.01 | Anti-bacterial porcelain floor tiles with chemical-resistant grout | 340.0 | m2
3.02 | 12-way surface mounted distribution board complete with surge protection | 4.0 | no
3.03 | SABS approved contractor PPE safety kits | 25.0 | no`,
  },
  {
    id: "wc-schools",
    name: "Western Cape Education Dept",
    badge: "Cape Town, WC (Roofing)",
    title: "Western Cape Education - High School Roofing & Perimeter Security",
    ref: "WCED-2026-049",
    region: "Western Cape",
    scheduleText: `Bill No. 1: Structural Timber & Roofing
1.01 | Treated timber roof trusses designed and fabricated to engineer specs | 380.0 | m2
1.02 | 0.5mm IBR Chromadek corrugated roof sheeting with fixings and flashing | 420.0 | m2
1.03 | Seamless aluminium rainwater gutters with downpipes | 160.0 | m

Bill No. 2: Perimeter Security & Earthworks
2.01 | Excavation in pickable earth for security fence post footings | 75.0 | m3
2.02 | 2.1m high galvanised anti-climb security mesh perimeter fencing | 450.0 | m
2.03 | PPE safety equipment sets: helmets, harnesses, high-vis vests | 20.0 | no`,
  },
];

export default function NewBoQPage() {
  const router = useRouter();
  const [selectedPresetId, setSelectedPresetId] = useState<string>("ethekwini-water");
  const [title, setTitle] = useState(TENDER_PRESETS[0].title);
  const [tenderRef, setTenderRef] = useState(TENDER_PRESETS[0].ref);
  const [region, setRegion] = useState(TENDER_PRESETS[0].region);
  const [inputMode, setInputMode] = useState<"upload" | "paste">("paste");
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState(TENDER_PRESETS[0].scheduleText);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyPreset = (preset: TenderPreset) => {
    setSelectedPresetId(preset.id);
    setTitle(preset.title);
    setTenderRef(preset.ref);
    setRegion(preset.region);
    setPastedText(preset.scheduleText);
    setInputMode("paste");
    setError(null);
  };

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
          <p className="text-xs text-slate-500">Provide tender details, choose a 1-click South African preset, or upload your PDF/Excel document.</p>
        </div>
        <a
          href="/contractor"
          className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg border border-slate-200"
        >
          Cancel
        </a>
      </div>

      {/* 1-Click SA Municipal Presets */}
      <div className="bg-gradient-to-r from-slate-900 to-blue-950 text-white p-5 rounded-2xl shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-blue-300">
            ⚡ Quick Demo Presets (South Africa)
          </span>
          <span className="text-[11px] text-slate-400">Click to load realistic municipal tender</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {TENDER_PRESETS.map((p) => {
            const isSelected = selectedPresetId === p.id && inputMode === "paste";
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => applyPreset(p)}
                className={`p-3 rounded-xl text-left border transition flex flex-col justify-between ${
                  isSelected
                    ? "bg-blue-600/30 border-blue-400 ring-1 ring-blue-400"
                    : "bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20"
                }`}
              >
                <div>
                  <div className="font-bold text-xs text-white">{p.name}</div>
                  <div className="text-[10px] text-blue-200 mt-0.5">{p.badge}</div>
                </div>
                <div className="text-[10px] text-emerald-400 font-semibold mt-2 font-mono">
                  {p.ref}
                </div>
              </button>
            );
          })}
        </div>
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
                <span className="text-[11px] text-slate-500">Multimodal &amp; Heuristic parser active</span>
              </div>
              <textarea
                rows={11}
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                placeholder="Paste tender bill of quantities, itemized schedules, or raw tables here..."
                className="w-full text-xs font-mono p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50"
              />
              <p className="text-[11px] text-slate-500">
                The parser will automatically identify Bill sections, descriptions, units, quantities, trade categories, and benchmark pricing hints.
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
                  {file ? `${(file.size / 1024).toFixed(1)} KB (Ready for multimodal AI parsing)` : "Drag and drop or browse tender PDF / Excel schedule"}
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
            <a
              href="/contractor"
              className="px-4 py-2.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </a>
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow transition flex items-center space-x-2 disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>AI Parsing Multi-Page BoQ...</span>
                </>
              ) : (
                <span>Create &amp; AI Parse BoQ &rarr;</span>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
