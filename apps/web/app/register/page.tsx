"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";

const CATEGORIES = [
  { id: "building-materials", label: "Building materials, cement, sand, stone and bricks" },
  { id: "concrete", label: "Concrete and reinforcing steel" },
  { id: "earthworks", label: "Civils and earthworks" },
];

const REGIONS = [
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

function initialAccountType(): "contractor" | "supplier" {
  if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("type") === "supplier") {
    return "supplier";
  }
  return "contractor";
}

export default function RegisterPage() {
  const router = useRouter();
  const [accountType, setAccountType] = useState<"contractor" | "supplier">(initialAccountType);
  const [legalName, setLegalName] = useState("");
  const [tradingName, setTradingName] = useState("");
  const [contactName, setContactName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [region, setRegion] = useState("KwaZulu-Natal");
  const [serviceRegions, setServiceRegions] = useState<string[]>(["KwaZulu-Natal"]);
  const [categories, setCategories] = useState<string[]>([]);
  const [contactMethod, setContactMethod] = useState<"email" | "whatsapp" | "sms">("email");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const toggleItem = (value: string, values: string[], setter: (next: string[]) => void) => {
    setter(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }
    if (accountType === "supplier" && (!categories.length || !serviceRegions.length)) {
      setError("Select at least one supply category and service region.");
      return;
    }

    setSubmitting(true);
    try {
      const session = await api.register({
        organisation_type: accountType,
        legal_name: legalName.trim(),
        trading_name: tradingName.trim() || undefined,
        email: email.trim().toLowerCase(),
        phone: phone.trim() || undefined,
        region,
        name: contactName.trim(),
        password,
        supplier_categories: accountType === "supplier" ? categories : [],
        supplier_service_regions: accountType === "supplier" ? serviceRegions : [],
        preferred_contact_method: contactMethod,
      });
      window.dispatchEvent(new Event("boqpro:session-changed"));
      const destination =
        session.organisation.type === "supplier" ? "/supplier" : "/contractor";
      router.replace(destination);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Registration failed. Please check your details and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:py-14">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <p className="text-xs font-bold uppercase tracking-wider text-amber-700">BoQPro account</p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Create your account</h1>
        <p className="mt-2 text-sm text-slate-600">
          Register your organisation to use BoQPro. Supplier applications are reviewed before receiving marketplace requests.
        </p>

        <div className="mt-6 grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1" role="group" aria-label="Account type">
          {(["contractor", "supplier"] as const).map((type) => (
            <button
              key={type}
              type="button"
              aria-pressed={accountType === type}
              onClick={() => setAccountType(type)}
              className={`rounded-lg px-3 py-2.5 text-sm font-semibold capitalize ${
                accountType === type ? "bg-white text-[#12233F] shadow-sm" : "text-slate-600"
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        {error && (
          <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </div>
        )}

        <form onSubmit={submit} className="mt-6 space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="legal-name" className="mb-1 block text-sm font-medium text-slate-700">Registered organisation name</label>
              <input id="legal-name" autoComplete="organization" required minLength={2} maxLength={255} value={legalName}
                onChange={(event) => setLegalName(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="trading-name" className="mb-1 block text-sm font-medium text-slate-700">Trading name <span className="font-normal text-slate-500">(optional)</span></label>
              <input id="trading-name" autoComplete="organization" maxLength={255} value={tradingName}
                onChange={(event) => setTradingName(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" />
            </div>
            <div>
              <label htmlFor="contact-name" className="mb-1 block text-sm font-medium text-slate-700">Your name</label>
              <input id="contact-name" autoComplete="name" required minLength={2} maxLength={255} value={contactName}
                onChange={(event) => setContactName(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" />
            </div>
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">Work email</label>
              <input id="email" type="email" autoComplete="email" required maxLength={255} value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" />
            </div>
            <div>
              <label htmlFor="phone" className="mb-1 block text-sm font-medium text-slate-700">Phone <span className="font-normal text-slate-500">(optional)</span></label>
              <input id="phone" type="tel" autoComplete="tel" maxLength={50} value={phone}
                onChange={(event) => setPhone(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" />
            </div>
            <div>
              <label htmlFor="region" className="mb-1 block text-sm font-medium text-slate-700">Organisation region</label>
              <select id="region" required value={region} onChange={(event) => setRegion(event.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100">
                {REGIONS.map((item) => <option key={item}>{item}</option>)}
              </select>
            </div>
          </div>

          {accountType === "supplier" && (
            <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div>
                <p className="text-sm font-semibold text-slate-800">Supplier application</p>
                <p className="mt-1 text-xs text-slate-600">Select the categories and areas you serve. You can update these later.</p>
              </div>
              <fieldset>
                <legend className="mb-2 text-sm font-medium text-slate-700">Supply categories</legend>
                <div className="space-y-2">
                  {CATEGORIES.map((category) => (
                    <label key={category.id} className="flex items-start gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={categories.includes(category.id)}
                        onChange={() => toggleItem(category.id, categories, setCategories)}
                        className="mt-0.5 accent-[#12233F]" />
                      {category.label}
                    </label>
                  ))}
                </div>
              </fieldset>
              <fieldset>
                <legend className="mb-2 text-sm font-medium text-slate-700">Service regions</legend>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {REGIONS.map((item) => (
                    <label key={item} className="flex items-center gap-2 text-xs text-slate-700">
                      <input type="checkbox" checked={serviceRegions.includes(item)}
                        onChange={() => toggleItem(item, serviceRegions, setServiceRegions)}
                        className="accent-[#12233F]" />
                      {item}
                    </label>
                  ))}
                </div>
              </fieldset>
              <div>
                <label htmlFor="contact-method" className="mb-1 block text-sm font-medium text-slate-700">Preferred quote-request contact method</label>
                <select id="contact-method" value={contactMethod} onChange={(event) => {
                  const value = event.target.value;
                  if (value === "email" || value === "whatsapp" || value === "sms") setContactMethod(value);
                }}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm">
                  <option value="email">Email</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="sms">SMS</option>
                </select>
              </div>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">Password</label>
              <input id="password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}
                value={password} onChange={(event) => setPassword(event.target.value)}
                aria-describedby="password-guidance"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" />
              <p id="password-guidance" className="mt-1 text-xs text-slate-500">Use at least 12 characters.</p>
            </div>
            <div>
              <label htmlFor="confirm-password" className="mb-1 block text-sm font-medium text-slate-700">Confirm password</label>
              <input id="confirm-password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}
                value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100" />
            </div>
          </div>

          <button type="submit" disabled={submitting}
            className="w-full rounded-lg bg-[#12233F] px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
            {submitting ? "Creating account..." : accountType === "supplier" ? "Submit supplier application" : "Create contractor account"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-600">
          Already have an account? <Link href="/login" className="font-semibold text-blue-700 hover:underline">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
