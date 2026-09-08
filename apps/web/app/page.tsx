"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
        <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#F4F1EA] border border-[#d5cfbe] text-[#12233F] text-xs font-semibold">
          <span>🇿🇦 Bid-Pricing Infrastructure for South African Contractors &amp; Suppliers</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-serif font-bold text-[#12233F] tracking-tight">
          Price it right. <span className="text-[#96731F]">Win it clean.</span>
        </h1>
        <p className="text-lg sm:text-xl font-medium text-slate-700">
          Defensible BoQ Pricing &amp; Verified Supplier-Quote Infrastructure
        </p>
        <p className="max-w-2xl mx-auto text-sm sm:text-base text-slate-600 leading-relaxed">
          Upload any Bill of Quantities or scope of work → get structured parsed line items → match verified local suppliers → compare competitive quotes → export a defensible, audit-backed tender submission.
        </p>
      </div>

      {/* Core Marketplace Loop Diagram / Steps */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-[#12233F] text-[#D9A94A] font-bold flex items-center justify-center mb-3">1</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Upload &amp; Process</h3>
          <p className="text-xs text-slate-600">Upload PDF, Excel or paste scope. Automatically extracts structured items with manual review and correction.</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-[#12233F] text-[#D9A94A] font-bold flex items-center justify-center mb-3">2</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Match &amp; Broadcast</h3>
          <p className="text-xs text-slate-600">System matches verified suppliers by trade category and province/region with countdown deadlines.</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-[#12233F] text-[#D9A94A] font-bold flex items-center justify-center mb-3">3</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Mobile Quote Submission</h3>
          <p className="text-xs text-slate-600">Suppliers receive notifications and submit unit rates from simple mobile interfaces.</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm relative">
          <div className="w-8 h-8 rounded-lg bg-[#12233F] text-[#D9A94A] font-bold flex items-center justify-center mb-3">4</div>
          <h3 className="font-semibold text-slate-900 text-sm mb-1">Compare &amp; Audit Export</h3>
          <p className="text-xs text-slate-600">Side-by-side comparison, select or manual override with audit reasons, and export to Excel/PDF.</p>
        </div>
      </div>

      {/* Two Portal Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Contractor Portal Card */}
        <div className="bg-white rounded-2xl border-2 border-[#12233F]/20 p-6 shadow-sm flex flex-col justify-between hover:border-[#12233F] transition">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-[#F4F1EA] text-[#12233F] border border-[#e2dccf]">
                Demand Side
              </span>
              <span className="text-xs text-slate-500 font-medium">Tendering Contractors</span>
            </div>
            <h2 className="text-2xl font-serif font-bold text-[#12233F]">Contractor Workspace</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Upload tender specifications, review processed BoQ tables, broadcast sourcing requests to matched suppliers, compare live incoming quotes, and generate export schedules.
            </p>
          </div>
          <div className="pt-6">
            <Link
              href="/contractor"
              className="block w-full text-center py-3 px-4 rounded-xl bg-[#12233F] hover:bg-[#1a335a] text-white font-semibold text-sm shadow transition"
            >
              Enter Contractor Portal &rarr;
            </Link>
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
            <h2 className="text-2xl font-serif font-bold text-slate-900">Supplier Portal</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              View active quote requests matched to your trade category and province. Submit line-item prices before the countdown deadline with turnaround notes.
            </p>
          </div>
          <div className="pt-6">
            <Link
              href="/supplier"
              className="block w-full text-center py-3 px-4 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-sm shadow transition"
            >
              Enter Supplier Portal (Mobile) &rarr;
            </Link>
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
