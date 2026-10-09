"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";

export default function SupplierRegistrationPage() {
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    legal_name: "",
    trading_name: "",
    contact_name: "",
    email: "",
    phone: "+27 ",
    password: "",
    categories: "building-materials",
  });

  const update = (field: string, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await api.registerSupplier({
        ...form,
        categories: form.categories.split(",").map((category) => category.trim()).filter(Boolean),
        service_regions: ["Durban", "KwaZulu-Natal"],
        preferred_contact_method: "email",
      });
      setSubmitted(true);
    } catch (registrationError: any) {
      setError(registrationError.message || "Registration could not be submitted.");
    }
  }

  if (submitted) {
    return (
      <main className="max-w-lg mx-auto bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Registration received</p>
        <h1 className="mt-3 text-3xl font-serif font-bold text-[#12233F]">Your profile is under review</h1>
        <p className="mt-4 text-sm leading-relaxed text-slate-600">
          BoQPro will review your Durban supplier profile before activating quote-request access.
        </p>
        <Link href="/supplier" className="inline-block mt-6 text-sm font-semibold text-[#12233F] underline">
          Return to supplier portal
        </Link>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto">
      <div className="mb-8">
        <p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Durban supplier network</p>
        <h1 className="mt-2 text-3xl font-serif font-bold text-[#12233F]">Register your supplier profile</h1>
        <p className="mt-3 text-sm text-slate-600">Start with your Durban and KwaZulu-Natal service coverage.</p>
      </div>

      <form onSubmit={submit} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
        {error && <p className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">{error}</p>}
        {[
          ["legal_name", "Legal name", "Durban Materials (Pty) Ltd"],
          ["trading_name", "Trading name", "Optional"],
          ["contact_name", "Primary contact", "Name and surname"],
          ["email", "Email address", "quotes@example.co.za"],
          ["phone", "Mobile number", "+27 82 000 0000"],
          ["password", "Password", "At least 12 characters"],
          ["categories", "Categories", "building-materials, concrete"],
        ].map(([field, label, placeholder]) => (
          <label key={field} className="block text-sm font-semibold text-slate-700">
            {label}
            <input
              required={field !== "trading_name"}
              type={field === "password" ? "password" : field === "email" ? "email" : "text"}
              value={form[field as keyof typeof form]}
              onChange={(event) => update(field, event.target.value)}
              placeholder={placeholder}
              minLength={field === "password" ? 12 : undefined}
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-700/20"
            />
          </label>
        ))}
        <button type="submit" className="w-full rounded-lg bg-emerald-700 px-4 py-3 text-sm font-bold text-white hover:bg-emerald-800">
          Submit supplier registration
        </button>
      </form>
    </main>
  );
}