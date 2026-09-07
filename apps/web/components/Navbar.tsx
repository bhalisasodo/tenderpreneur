"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, AuthSession, UserDTO } from "../lib/api";

const PERSONA_EMOJIS: Record<string, string> = {
  contractor: "👷",
  supplier: "🧱",
};

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [tenants, setTenants] = useState<UserDTO[]>([]);
  const [currentSession, setCurrentSession] = useState<AuthSession | null>(null);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    // 1. Load active session from localStorage
    const saved = localStorage.getItem("tp_session");
    if (saved) {
      try {
        setCurrentSession(JSON.parse(saved));
      } catch {}
    }

    // 2. Load demo tenants
    api.getDemoTenants().then((users) => {
      setTenants(users);
      // If no active session, initialize with first contractor
      if (!saved && users.length > 0) {
        const defaultContractor = users.find((u) => u.organisation?.type === "contractor") || users[0];
        handleSwitchPersona(defaultContractor.email);
      }
    }).catch(() => {});
  }, []);

  const handleSwitchPersona = async (email: string) => {
    try {
      setSwitching(true);
      const session = await api.login(email);
      setCurrentSession(session);

      // Contextual routing: if switching to supplier, send to /supplier; if contractor, send to /contractor
      if (session.organisation.type === "supplier") {
        if (!pathname.startsWith("/supplier")) {
          router.push("/supplier");
        } else {
          window.location.reload();
        }
      } else {
        if (!pathname.startsWith("/contractor") && pathname !== "/") {
          router.push("/contractor");
        } else {
          window.location.reload();
        }
      }
    } catch (err: any) {
      alert("Failed to switch persona: " + err.message);
    } finally {
      setSwitching(false);
    }
  };

  const isSupplierView = pathname.startsWith("/supplier");
  const isContractorView = pathname.startsWith("/contractor");

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-50 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center font-black text-xl text-white shadow">
              T
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-white">Tenderpreneur</span>
              <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 uppercase tracking-wide">
                MVP
              </span>
            </div>
          </Link>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center space-x-1 text-xs font-semibold">
          <Link
            href="/contractor"
            className={`px-3 py-1.5 rounded-lg transition ${
              isContractorView
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-300 hover:text-white hover:bg-slate-800"
            }`}
          >
            👷 Contractor Portal
          </Link>
          <Link
            href="/supplier"
            className={`px-3 py-1.5 rounded-lg transition ${
              isSupplierView
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-300 hover:text-white hover:bg-slate-800"
            }`}
          >
            🧱 Supplier Portal (Mobile)
          </Link>
        </nav>

        {/* Global Persona Switcher */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2 bg-slate-800/90 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-xs">
            <span className="text-[11px] text-slate-400 font-semibold hidden sm:inline">
              Persona:
            </span>
            <select
              value={currentSession?.user.email || ""}
              onChange={(e) => handleSwitchPersona(e.target.value)}
              disabled={switching || tenants.length === 0}
              aria-label="Active Demo Persona"
              className="bg-transparent text-white font-bold text-xs focus:outline-none cursor-pointer pr-1"
            >
              {tenants.map((u) => {
                const orgType = u.organisation?.type || "user";
                const orgName = u.organisation?.legal_name || "Demo Org";
                const emoji = PERSONA_EMOJIS[orgType] || "👤";
                return (
                  <option key={u.id} value={u.email} className="bg-slate-900 text-white py-1">
                    {emoji} {u.name} ({orgName} - {orgType.toUpperCase()})
                  </option>
                );
              })}
            </select>
            {switching && (
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
