"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";

const ALL_CATEGORIES = [
  { id: "building-materials", label: "Building Materials & Cement" },
  { id: "concrete", label: "Concrete & Ready-Mix" },
  { id: "earthworks", label: "Earthworks & Plant Hire" },
  { id: "roofing", label: "Roofing & Timber" },
  { id: "plumbing", label: "Plumbing & Drainage" },
  { id: "electrical", label: "Electrical" },
  { id: "ppe", label: "Safety Equipment & PPE" },
  { id: "finishes", label: "Finishes, Paint & Tiles" },
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

export default function SupplierProfilePage() {
  const [categories, setCategories] = useState<string[]>([]);
  const [regions, setRegions] = useState<string[]>([]);
  const [contactMethod, setContactMethod] = useState("whatsapp");
  const [bbeeLevel, setBbeeLevel] = useState("1");
  const [cidbGrade, setCidbGrade] = useState("6GB");
  const [status, setStatus] = useState<"pending" | "approved" | "rejected" | "suspended">("pending");
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState(false);

  useEffect(() => {
    // Fetch profile
    api.getSupplierProfile()
      .then((data) => {
        if (data && data.categories) {
          setCategories(data.categories || []);
          setRegions(data.service_regions || []);
          setContactMethod(data.preferred_contact_method || "whatsapp");
          setStatus(data.status || "pending");
          setActive(Boolean(data.active));
          if (data.compliance_flags) {
            setBbeeLevel(data.compliance_flags.bbee_level || "1");
            setCidbGrade(data.compliance_flags.cidb_grade || "");
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const toggleCategory = (id: string) => {
    setCategories((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const toggleRegion = (r: string) => {
    setRegions((prev) =>
      prev.includes(r) ? prev.filter((reg) => reg !== r) : [...prev, r]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setSaving(true);
      setSavedMessage(false);
      await api.updateSupplierProfile({
        categories,
        service_regions: regions,
        compliance_flags: { bbee_level: bbeeLevel, cidb_grade: cidbGrade, csd_registered: true },
        preferred_contact_method: contactMethod,
        active: true,
      });
      setSavedMessage(true);
      setTimeout(() => setSavedMessage(false), 3000);
    } catch (err: any) {
      alert("Failed to save profile: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-xs text-slate-500">Loading supplier profile...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link
          href="/supplier"
          className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-slate-900"
        >
          &larr; Back to Quote Requests
        </Link>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-slate-900 text-base">Trade &amp; Region Profile</h3>
          <p className="text-xs text-slate-500">
            Configure the categories and regions you supply to receive automated matching quote requests.
          </p>
        </div>

        <div className={`rounded-xl border p-3 text-xs ${
          status === "approved"
            ? "border-emerald-200 bg-emerald-50 text-emerald-900"
            : status === "rejected"
              ? "border-rose-200 bg-rose-50 text-rose-900"
              : status === "suspended"
                ? "border-amber-200 bg-amber-50 text-amber-900"
                : "border-slate-200 bg-slate-50 text-slate-700"
        }`}>
          <div className="flex items-center justify-between gap-3">
            <span className="font-bold capitalize">{status}</span>
            <span>{active ? "Marketplace active" : "Marketplace inactive"}</span>
          </div>
          <p className="mt-1">
            {status === "approved"
              ? "You are approved and can receive quote requests."
              : status === "rejected"
                ? "Your supplier application has been rejected. Contact the platform administrator for details."
                : status === "suspended"
                  ? "Your marketplace access has been suspended. Contact the platform administrator."
                  : "Your application is under review. This status will update here after the platform review."}
          </p>
        </div>

        {savedMessage && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-bold text-center">
            ✓ Supplier profile saved successfully!
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-5">
          {/* Categories */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-800">
              Supply Categories (Select all that apply)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {ALL_CATEGORIES.map((cat) => {
                const checked = categories.includes(cat.id);
                return (
                  <button
                    type="button"
                    key={cat.id}
                    onClick={() => toggleCategory(cat.id)}
                    className={`p-2.5 rounded-xl text-left border text-xs transition flex items-center justify-between ${
                      checked
                        ? "bg-blue-50 border-blue-500 text-blue-900 font-semibold"
                        : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    <span>{cat.label}</span>
                    <span>{checked ? "✓" : "+"}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Service Regions */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-800">
              Service Provinces / Regions
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {ALL_REGIONS.map((r) => {
                const checked = regions.includes(r);
                return (
                  <button
                    type="button"
                    key={r}
                    onClick={() => toggleRegion(r)}
                    className={`p-2 rounded-lg text-left border text-xs transition flex items-center justify-between ${
                      checked
                        ? "bg-emerald-50 border-emerald-500 text-emerald-900 font-semibold"
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

          {/* Preferred Contact & Compliance */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-slate-100">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Preferred Notification Channel
              </label>
              <select
                value={contactMethod}
                onChange={(e) => setContactMethod(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-xl border border-slate-300 bg-white"
              >
                <option value="whatsapp">WhatsApp (Instant alert)</option>
                <option value="email">Email</option>
                <option value="sms">SMS</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                B-BBEE Recognition Level
              </label>
              <select
                value={bbeeLevel}
                onChange={(e) => setBbeeLevel(e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-xl border border-slate-300 bg-white"
              >
                <option value="1">Level 1 Contributor (135% recognition)</option>
                <option value="2">Level 2 Contributor (125% recognition)</option>
                <option value="3">Level 3 Contributor</option>
                <option value="4">Level 4 Contributor</option>
                <option value="Non-Compliant">Non-Compliant</option>
              </select>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100">
            <button
              type="submit"
              disabled={saving}
              className="w-full py-3 rounded-xl bg-slate-900 hover:bg-black text-white font-bold text-xs shadow transition"
            >
              {saving ? "Saving Profile..." : "Save Matching Preferences"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
