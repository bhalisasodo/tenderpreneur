"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";

function safeNextPath(): string | null {
  const next = new URLSearchParams(window.location.search).get("next");
  return next?.startsWith("/") && !next.startsWith("//") ? next : null;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const session = await api.login(email.trim().toLowerCase(), password);
      window.dispatchEvent(new Event("boqpro:session-changed"));
      const defaultPath =
        session.user.role === "platform_operator"
          ? "/operator/suppliers"
          : session.organisation.type === "supplier"
            ? "/supplier"
            : "/contractor";
      router.replace(safeNextPath() || defaultPath);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sign in failed. Check your details and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-12">
      <section className="w-full rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wider text-amber-700">BoQPro account</p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Sign in</h1>
        <p className="mt-2 text-sm text-slate-600">Use the email address and password linked to your account.</p>

        {error && (
          <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </div>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-[#12233F] px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="mt-5 text-center text-xs text-slate-500">
          New to BoQPro? Create an account to start a contractor workspace or apply as a supplier.
        </p>
        <div className="mt-4 text-center">
          <Link href="/register" className="text-sm font-semibold text-blue-700 hover:underline">
            Create an account
          </Link>
        </div>
        <div className="mt-4 text-center">
          <Link href="/" className="text-xs font-semibold text-blue-700 hover:underline">Back to BoQPro</Link>
        </div>
      </section>
    </main>
  );
}
