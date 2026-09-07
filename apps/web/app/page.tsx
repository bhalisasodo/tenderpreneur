"use client";

import { useEffect, useState } from "react";
import { api, UserDTO } from "../lib/api";

export default function Home() {
  const [demoUsers, setDemoUsers] = useState<UserDTO[]>([]);
  const [currentUser, setCurrentUser] = useState<string | null>(null);

  useEffect(() => {
    // Fetch available seeded demo personas
    api.getDemoTenants().then((users) => {
      setDemoUsers(users);
      if (users.length > 0 && !localStorage.getItem("tp_token")) {
        // Default login as contractor
        const contractor = users.find((u) => u.organisation?.type === "contractor") || users[0];
        api.login(contractor.email).then((s) => setCurrentUser(s.user.email));
      } else {
        const sess = localStorage.getItem("tp_session");
        if (sess) {
          try {
            setCurrentUser(JSON.parse(sess).user.email);
          } catch {}
        }
      }
    }).catch(() => {});
  }, []);

  const handleSelectPersona = async (email: string) => {
    try {
      const res = await api.login(email);
      setCurrentUser(res.user.email);
      if (res.organisation.type === "contractor") {
        window.location.href = "/contractor";
      } else {
        window.location.href = "/supplier";
      }
    } catch (err: any) {
      alert("Failed to switch persona: " + err.message);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-12">
      {/* Hero Section */}
      <div className="text-center space-y-4 pt-6 pb-2">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold">
          <span>🇿🇦 Built for South African Tender Contractors &amp; Suppliers</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight">
          AI BoQ Pricing &amp; <br />
          <span className="text-blue-600">Verified Supplier-Quote Marketplace</span>
        </h1>
        <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-600 leading-relaxed">
          Upload a Bill of Quantities or scope of work → get structured parsed line items → match local verified suppliers → compare competitive quotes → export a submission-ready, audit-backed tender price before your deadline.
        </p>
      </div>

      {/* Core Marketplace Loop Diagram / Steps */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 font-bold flex items-center justify-center mb-3">1</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Upload &amp; AI Parse</h3>
          <p className="text-xs text-slate-600">Upload PDF, Excel or paste scope. Model extracts structured items with manual correction.</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center mb-3">2</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Match &amp; Broadcast</h3>
          <p className="text-xs text-slate-600">System matches verified suppliers by trade category and province/region with countdown deadlines.</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center mb-3">3</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Mobile Quote Submission</h3>
          <p className="text-xs text-slate-600">Suppliers receive notifications and submit unit rates from simple mobile interfaces.</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 font-bold flex items-center justify-center mb-3">4</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Compare &amp; Audit Export</h3>
          <p className="text-xs text-slate-600">Side-by-side comparison, select or manual override with audit reasons, and export to Excel/PDF.</p>
        </div>
      </div>

      {/* Two Portal Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Contractor Portal Card */}
        <div className="bg-white rounded-2xl border-2 border-blue-600/30 p-6 shadow-sm flex flex-col justify-between hover:border-blue-600 transition">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-blue-100 text-blue-800">
                Demand Side
              </span>
              <span className="text-xs text-slate-500 font-medium">Tendering Contractors</span>
            </div>
            <h2 className="text-2xl font-bold text-slate-900">Contractor Workspace</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Upload tender specifications, review AI-parsed BoQ tables, broadcast sourcing requests to matched suppliers, compare live incoming quotes, and generate export schedules.
            </p>
          </div>
          <div className="pt-6">
            <a
              href="/contractor"
              className="block w-full text-center py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow transition"
            >
              Enter Contractor Portal &rarr;
            </a>
          </div>
        </div>

        {/* Supplier Portal Card */}
        <div className="bg-white rounded-2xl border-2 border-emerald-600/30 p-6 shadow-sm flex flex-col justify-between hover:border-emerald-600 transition">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-emerald-100 text-emerald-800">
                Supply Side
              </span>
              <span className="text-xs text-slate-500 font-medium">Mobile-First Submissions</span>
            </div>
            <h2 className="text-2xl font-bold text-slate-900">Supplier Portal</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              View active quote requests matched to your trade category and province. Submit line-item prices before the countdown deadline with turnaround notes.
            </p>
          </div>
          <div className="pt-6">
            <a
              href="/supplier"
              className="block w-full text-center py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm shadow transition"
            >
              Enter Supplier Portal (Mobile) &rarr;
            </a>
          </div>
        </div>
      </div>

      {/* Demo Persona Switcher */}
      {demoUsers.length > 0 && (
        <div className="bg-slate-100 rounded-2xl p-6 border border-slate-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Interactive Demo Persona Switcher</h3>
              <p className="text-xs text-slate-600">Switch between pre-seeded test organisations with one click to simulate the full marketplace:</p>
            </div>
            {currentUser && (
              <span className="text-xs px-3 py-1 rounded-full bg-white border border-slate-300 text-slate-700 font-medium">
                Active: <strong className="text-blue-600">{currentUser}</strong>
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {demoUsers.map((user) => {
              const isContractor = user.organisation?.type === "contractor";
              const isActive = currentUser === user.email;
              return (
                <button
                  key={user.id}
                  onClick={() => handleSelectPersona(user.email)}
                  className={`p-3.5 rounded-xl text-left border text-xs transition relative flex flex-col justify-between ${
                    isActive
                      ? "bg-white border-blue-600 ring-2 ring-blue-500/20 shadow-sm"
                      : "bg-white/80 border-slate-200 hover:bg-white hover:border-slate-300"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                          isContractor ? "bg-blue-100 text-blue-800" : "bg-emerald-100 text-emerald-800"
                        }`}
                      >
                        {user.organisation?.type}
                      </span>
                      <span className="text-[10px] text-slate-500">{user.organisation?.region}</span>
                    </div>
                    <div className="font-semibold text-slate-900 truncate">{user.organisation?.legal_name}</div>
                    <div className="text-slate-500 truncate">{user.email}</div>
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-medium text-blue-600">
                    <span>{isActive ? "✓ Active Session" : "Switch Persona"}</span>
                    <span>&rarr;</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
