"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, AuthSession } from "../../lib/api";

export default function ContractorLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setSession(null);
    setError(null);
    if (!localStorage.getItem("tp_token")) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    api.getMe().then((current) => {
      if (!active) return;
      if (current.organisation.type !== "contractor" && current.user.role !== "platform_operator") {
        router.replace(current.organisation.type === "supplier" ? "/supplier" : "/login");
        return;
      }
      setSession(current);
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not verify your sign-in.");
    });

    return () => { active = false; };
  }, [pathname, router]);

  if (error) {
    return (
      <div role="alert" className="mx-auto max-w-lg rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800">
        <p>{error}</p>
        <Link href={`/login?next=${encodeURIComponent(pathname)}`} className="mt-3 inline-block font-semibold underline">
          Sign in again
        </Link>
      </div>
    );
  }

  if (!session) return <p className="py-16 text-center text-sm text-slate-500">Verifying your sign-in...</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:p-5">
        <div>
          <div className="text-xs font-medium text-slate-500">
            Organisation: <strong className="text-slate-800">{session.organisation.legal_name}</strong>
            {session.organisation.region ? ` (${session.organisation.region})` : ""}
          </div>
          <h2 className="mt-1 text-xl font-bold text-slate-900">Tender BoQ Estimator &amp; Sourcing Hub</h2>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/contractor" className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
            All BoQs
          </Link>
          <Link href="/contractor/boqs/new" className="rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-blue-700">
            Upload new BoQ
          </Link>
        </div>
      </div>
      {children}
    </div>
  );
}
