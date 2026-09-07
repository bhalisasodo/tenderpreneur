"use client";

import { useEffect, useState } from "react";
import { api, AuthSession } from "../../lib/api";

export default function ContractorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    // Verify session
    const stored = localStorage.getItem("tp_session");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.organisation.type === "contractor") {
          setSession(parsed);
        } else {
          // If logged in as supplier, switch to contractor
          api.login("estimator@amandlacivils.co.za").then(setSession).catch(() => {});
        }
      } catch {}
    } else {
      api.login("estimator@amandla.co.za").catch(() => {
        api.login("estimator@amandlacivils.co.za").then(setSession).catch(() => {});
      });
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Contractor Header Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-blue-100 text-blue-800">
              Contractor Portal
            </span>
            <span className="text-xs text-slate-500 font-medium">
              Organisation: <strong className="text-slate-800">{session?.organisation.legal_name || "Amandla Civils (Pty) Ltd"}</strong> ({session?.organisation.region || "KwaZulu-Natal"})
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">Tender BoQ Estimator &amp; Sourcing Hub</h2>
        </div>

        <div className="flex items-center space-x-3">
          <a
            href="/contractor"
            className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
          >
            All BoQs
          </a>
          <a
            href="/contractor/boqs/new"
            className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition flex items-center space-x-1"
          >
            <span>+</span>
            <span>Upload New BoQ</span>
          </a>
        </div>
      </div>

      <div>{children}</div>
    </div>
  );
}
