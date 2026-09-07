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

  // Backend / Demo Mode Settings Modal
  const [showModal, setShowModal] = useState(false);
  const [isMockMode, setIsMockMode] = useState(true);
  const [customUrl, setCustomUrl] = useState("");
  const [savingUrl, setSavingUrl] = useState(false);

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

    // 3. Initialize mock mode state and API URL
    setIsMockMode(api.isMockMode());
    setCustomUrl(api.getApiBase());
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

  const handleSaveApiUrl = (e: React.FormEvent) => {
    e.preventDefault();
    setSavingUrl(true);
    try {
      if (customUrl.trim().length > 0) {
        api.setApiBase(customUrl.trim());
        api.setMockMode(false);
      } else {
        api.setApiBase(null);
        api.setMockMode(true);
      }
      setIsMockMode(api.isMockMode());
      setShowModal(false);
      window.location.reload();
    } finally {
      setSavingUrl(false);
    }
  };

  const handleSwitchToDemoMode = () => {
    api.setMockMode(true);
    api.setApiBase(null);
    setIsMockMode(true);
    setShowModal(false);
    window.location.reload();
  };

  const handleResetData = () => {
    if (confirm("Reset demo data back to default South African tenders and suppliers?")) {
      api.resetDemoData();
      window.location.reload();
    }
  };

  const isContractorView = pathname.startsWith("/contractor");
  const isSupplierView = pathname.startsWith("/supplier");

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

        {/* Global Persona Switcher & API Status */}
        <div className="flex items-center space-x-2">
          {/* Environment / Backend Status Badge */}
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-800 text-xs font-semibold transition"
            title="Configure Backend API / Demo Mode"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isMockMode ? "bg-amber-400" : "bg-emerald-400"
              }`}
            ></span>
            <span className="text-[11px] text-slate-300 hidden sm:inline">
              {isMockMode ? "⚡ In-Browser Mode" : "🟢 Live API"}
            </span>
          </button>

          {/* Persona Switcher */}
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

      {/* Backend / Demo Mode Configuration Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white text-slate-900 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-xl">⚙️</span>
                <h3 className="font-bold text-slate-900 text-base">Backend &amp; Demo Settings</h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div
                className={`p-3 rounded-xl border ${
                  isMockMode
                    ? "bg-amber-50 border-amber-200 text-amber-900"
                    : "bg-emerald-50 border-emerald-200 text-emerald-900"
                }`}
              >
                <div className="font-bold">
                  {isMockMode
                    ? "⚡ Running in In-Browser Demo Mode"
                    : "🟢 Connected to External Backend API"}
                </div>
                <div className="text-[11px] mt-0.5 opacity-90">
                  {isMockMode
                    ? "Tenderpreneur is running 100% in your browser using local storage persistence with South African seed tenders & suppliers. No external backend required."
                    : `Currently sending requests to: ${api.getApiBase()}`}
                </div>
              </div>

              <form onSubmit={handleSaveApiUrl} className="space-y-3 pt-1">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Connect External Backend API URL (Optional)
                  </label>
                  <input
                    type="url"
                    value={customUrl}
                    onChange={(e) => setCustomUrl(e.target.value)}
                    placeholder="https://your-api.onrender.com/api/v1"
                    className="w-full p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-xs font-mono"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Enter the URL of your deployed FastAPI server (e.g. on Render, Railway, or Fly.io).
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <button
                    type="button"
                    onClick={handleSwitchToDemoMode}
                    className="px-3 py-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 font-semibold text-xs"
                  >
                    Use In-Browser Demo
                  </button>

                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={handleResetData}
                      className="px-3 py-2 rounded-lg text-rose-700 bg-rose-50 hover:bg-rose-100 font-semibold text-xs"
                    >
                      Reset Demo Data
                    </button>
                    <button
                      type="submit"
                      disabled={savingUrl}
                      className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow"
                    >
                      {savingUrl ? "Saving..." : "Save & Connect"}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
