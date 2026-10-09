"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "../../lib/api";

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authorized, setAuthorized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setAuthorized(false);
    setError(null);
    if (!localStorage.getItem("tp_token")) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return () => { active = false; };
    }

    api.getMe().then((session) => {
      if (!active) return;
      if (session.user.role !== "platform_operator") {
        router.replace(session.organisation.type === "supplier" ? "/supplier" : "/contractor");
        return;
      }
      setAuthorized(true);
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
  if (!authorized) return <p className="py-16 text-center text-sm text-slate-500">Verifying your sign-in...</p>;
  return children;
}
