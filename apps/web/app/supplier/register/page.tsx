"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "../../../lib/api";

const ALL_CATEGORIES = [
  { id: "building-materials", label: "Building Materials & Cement", icon: "🧱" },
  { id: "concrete", label: "Concrete & Ready-Mix", icon: "🏗️" },
  { id: "earthworks", label: "Earthworks & Plant Hire", icon: "🚜" },
  { id: "roofing", label: "Roofing & Timber", icon: "🏠" },
  { id: "plumbing", label: "Plumbing & Drainage", icon: "🔧" },
  { id: "electrical", label: "Electrical & Lighting", icon: "⚡" },
  { id: "ppe", label: "Safety Equipment & PPE", icon: "🦺" },
  { id: "finishes", label: "Finishes, Paint & Tiles", icon: "🎨" },
];

const ALL_REGIONS = [
  "KwaZulu-Natal",
  "Gauteng",
  "Western Cape",
  "Eastern Cape",
  "Free State",
  "Mpumalanga",
  "Limpopo",
  "North West",
  "Northern Cape",
];

export default function SupplierRegisterPage() {
  const router = useRouter();

  // Form State
  const [legalName, setLegalName] = useState("");
  const [tradingName, setTradingName] = useState("");
  const [contactName, setContactName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [primaryRegion, setPrimaryRegion] = useState("KwaZulu-Natal");
  const [password, setPassword] = useState("");
  const [categories, setCategories] = useState<string[]>(["building-materials"]);
  const [serviceRegions, setServiceRegions] = useState<string[]>(["KwaZulu-Natal"]);
  const [contactMethod, setContactMethod] = useState("whatsapp");
  const [bbeeLevel, setBbeeLevel] = useState("1");
  const [csdNumber, setCsdNumber] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleCategory = (id: string) => {
    setCategories((prev) =>
      prev.includes(id) ? (prev.length > 1 ? prev.filter((c) => c !== id) : prev) : [...prev, id]
    );
  };

  const toggleRegion = (r: string) => {
    setServiceRegions((prev) =>
      prev.includes(r) ? (prev.length > 1 ? prev.filter((reg) => reg !== r) : prev) : [...prev, r]
    );
  };

  const selectAllRegions = () => {
    setServiceRegions(ALL_REGIONS);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!legalName || !contactName || !email || !phone || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    if (categories.length === 0) {
      setError("Please select at least one supply category.");
      return;
    }

    if (serviceRegions.length === 0) {
      setError("Please select at least one service province.");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      await api.registerSupplier({
        legal_name: legalName.trim(),
        trading_name: tradingName.trim() || undefined,
        contact_name: contactName.trim(),
        email: email.trim().toLowerCase(),
        phone: phone.trim(),
        region: primaryRegion,
        password,
        categories,
        service_regions: serviceRegions,
        preferred_contact_method: contactMethod,
        compliance_flags: {
          bbee_level: bbeeLevel,
          csd_number: csdNumber.trim() || undefined,
          csd_registered: Boolean(csdNumber.trim()),
        },
      });

      router.push("/supplier/welcome");
    } catch (err: any) {
      setError(err.message || "Failed to complete registration.");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 py-6 px-4 sm:px-6">
      {/* Header Banner */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
          <span>🇿🇦 BoQPro Supplier Marketplace</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-serif font-bold text-[#12233F]">
          Register as a Verified Trade Supplier
        </h1>
        <p className="text-sm sm:text-base text-slate-600 max-w-xl mx-auto leading-relaxed">
          Receive matched Requests for Quotation (RFQs) from South African contractors preparing live tender bids. Respond from WhatsApp or mobile in seconds.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-xs font-semibold">
          {error}
        </div>
      )}

      {/* Registration Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-8">
        {/* Section 1: Business Details */}
        <div className="space-y-4">
          <div className="border-b border-slate-100 pb-2">
            <h3 className="text-base font-bold text-slate-900">1. Business &amp; Contact Details</h3>
            <p className="text-xs text-slate-500">Provide your official company details and quotation dispatch contact.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Company Legal Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Durban Building Supplies (Pty) Ltd"
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Trading Name <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Durban Builders Hub"
                value={tradingName}
                onChange={(e) => setTradingName(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Primary Contact Person <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Thabo Ndlovu (Sales Manager)"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Business Email Address <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                required
                placeholder="sales@yourcompany.co.za"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Mobile / WhatsApp Number <span className="text-red-500">*</span>
              </label>
              <input
                type="tel"
                required
                placeholder="e.g. +27 82 123 4567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none font-mono"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                Instant quote alerts and 1-click pricing links will be sent here.
              </span>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Primary Depot / Province <span className="text-red-500">*</span>
              </label>
              <select
                value={primaryRegion}
                onChange={(e) => setPrimaryRegion(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              >
                {ALL_REGIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Section 2: Supply Categories */}
        <div className="space-y-3">
          <div className="border-b border-slate-100 pb-2 flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">2. Supply Categories</h3>
              <p className="text-xs text-slate-500">Select all trade materials and services your firm supplies.</p>
            </div>
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
              {categories.length} selected
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {ALL_CATEGORIES.map((cat) => {
              const checked = categories.includes(cat.id);
              return (
                <button
                  type="button"
                  key={cat.id}
                  onClick={() => toggleCategory(cat.id)}
                  className={`p-3 rounded-xl text-left border text-xs transition flex items-center justify-between ${
                    checked
                      ? "bg-emerald-50 border-emerald-500 text-emerald-900 font-bold shadow-sm"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <span className="flex items-center space-x-2">
                    <span className="text-base">{cat.icon}</span>
                    <span>{cat.label}</span>
                  </span>
                  <span>{checked ? "✓" : "+"}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 3: Service Provinces */}
        <div className="space-y-3">
          <div className="border-b border-slate-100 pb-2 flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">3. Service Delivery Provinces</h3>
              <p className="text-xs text-slate-500">Provinces where your fleet or couriers deliver to construction sites.</p>
            </div>
            <button
              type="button"
              onClick={selectAllRegions}
              className="text-xs text-emerald-700 hover:text-emerald-900 font-bold underline"
            >
              Select All (National)
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {ALL_REGIONS.map((r) => {
              const checked = serviceRegions.includes(r);
              return (
                <button
                  type="button"
                  key={r}
                  onClick={() => toggleRegion(r)}
                  className={`p-2.5 rounded-lg text-left border text-xs transition flex items-center justify-between ${
                    checked
                      ? "bg-emerald-50 border-emerald-500 text-emerald-900 font-bold"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <span className="truncate">{r}</span>
                  <span>{checked ? "✓" : "+"}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Section 4: Self-Declared Compliance */}
        <div className="space-y-4">
          <div className="border-b border-slate-100 pb-2">
            <h3 className="text-base font-bold text-slate-900">4. South African Compliance (Self-Declared)</h3>
            <p className="text-xs text-slate-500">Boosts matching priority for public sector and municipal tenders.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                B-BBEE Contributor Level
              </label>
              <select
                value={bbeeLevel}
                onChange={(e) => setBbeeLevel(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              >
                <option value="1">Level 1 (135% Recognition)</option>
                <option value="2">Level 2 (125% Recognition)</option>
                <option value="3">Level 3 (110% Recognition)</option>
                <option value="4">Level 4 (100% Recognition)</option>
                <option value="Non-Compliant">Non-Compliant</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                CSD Registration Number <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                placeholder="e.g. MAAA0123456"
                value={csdNumber}
                onChange={(e) => setCsdNumber(e.target.value)}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none font-mono"
              />
            </div>
          </div>
        </div>

        {/* Section 5: Account Security */}
        <div className="space-y-4">
          <div className="border-b border-slate-100 pb-2">
            <h3 className="text-base font-bold text-slate-900">5. Account Security</h3>
            <p className="text-xs text-slate-500">Create a password to manage your quotes and company profile.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Account Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              required
              minLength={6}
              placeholder="Minimum 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Terms & Submit */}
        <div className="pt-2 space-y-4">
          <div className="text-[11px] text-slate-500">
            By registering, you agree to receive urgent tender quotation requests matching your chosen trades and provinces. No subscription fee applies during MVP.
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm shadow-md transition disabled:opacity-50 flex items-center justify-center space-x-2"
          >
            {loading ? (
              <span>Activating Supplier Account...</span>
            ) : (
              <span>Complete Registration &amp; Start Quoting &rarr;</span>
            )}
          </button>

          <div className="text-center text-xs text-slate-500">
            Already registered?{" "}
            <Link href="/" className="text-emerald-700 font-bold hover:underline">
              Switch or sign in to your existing account
            </Link>
          </div>
        </div>
      </form>
    </div>
  );
}
