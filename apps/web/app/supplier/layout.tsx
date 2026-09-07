"use client";

import { useEffect, useState } from "react";
import { api, AuthSession } from "../../lib/api";

export default function SupplierLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("tp_session");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.organisation.type === "supplier") {
          setSession(parsed);
        } else {
          // Switch to supplier 1 by default
          api.login("sales@durbanbuilders.co.za").then(setSession).catch(() => {});
        }
      } catch {}
    } else {
      api.login("sales@durbanbuilders.co.za").then(setSession).catch(() => {});
    }
  }, []);

  return (
    <div className="max-w-xl mx-auto space-y-5">
      {/* Mobile-Optimized Supplier Header */}
      <div className="bg-slate-900 text-white rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500 text-white">
              Supplier Portal (Mobile)
            </span>
          </div>
          <span className="text-xs text-slate-400">
            {session?.organisation.region || "KwaZulu-Natal"}
          </span>
        </div>
        <h2 className="text-lg font-bold mt-2 truncate">
          {session?.organisation.legal_name || "Durban Building Supplies"}
        </h2>
        <div className="text-xs text-slate-400 mt-0.5">
          {session?.user.name} &bull; {session?.user.email}
        </div>
      </div>

      <div>{children}</div>
    </div>
  );
}
