"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, AuthSession } from "../../lib/api";

export default function SupplierLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [directRfqLink, setDirectRfqLink] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setSession(null);
    setError(null);

    if (new URLSearchParams(window.location.search).has("access_token")) {
      setDirectRfqLink(true);
      return () => { active = false; };
    }

    setDirectRfqLink(false);
    if (!localStorage.getItem("tp_token")) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return () => { active = false; };
    }

    api.getMe().then((current) => {
      if (!active) return;
      if (current.organisation.type !== "supplier" && current.user.role !== "platform_operator") {
        router.replace(current.organisation.type === "contractor" ? "/contractor" : "/login");
        return;
      }
      setSession(current);
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not verify your sign-in.");
    });

    return () => { active = false; };
  }, [pathname, router]);

  if (directRfqLink) return <div className="mx-auto max-w-xl">{children}</div>;

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
    <div className="mx-auto max-w-xl space-y-5">
      <div className="rounded-2xl bg-slate-900 p-5 text-white shadow-sm">
        <div className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-300">Supplier portal</div>
        <h2 className="mt-2 truncate text-lg font-bold">{session.organisation.legal_name}</h2>
        <div className="mt-0.5 text-xs text-slate-300">
          {session.user.name} &bull; {session.user.email}
        </div>
      </div>
      {children}
    </div>
  );
}
