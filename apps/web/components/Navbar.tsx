"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, AuthSession } from "../lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

  useEffect(() => {
    const refreshSession = () => {
      const stored = localStorage.getItem("tp_session");
      if (!stored) {
        setSession(null);
        return;
      }
      try {
        setSession(JSON.parse(stored) as AuthSession);
      } catch {
        api.logout();
        setSession(null);
      }
    };

    refreshSession();
    window.addEventListener("boqpro:session-changed", refreshSession);
    window.addEventListener("boqpro:session-expired", refreshSession);
    return () => {
      window.removeEventListener("boqpro:session-changed", refreshSession);
      window.removeEventListener("boqpro:session-expired", refreshSession);
    };
  }, [pathname]);

  const signOut = () => {
    api.logout();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-[#1f3760] bg-[#12233F] text-white shadow-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center space-x-2.5">
          <img
            src={`${basePath}/boqpro-logo-horizontal-reversed.svg`}
            alt="BoQPro"
            className="h-9 w-auto"
          />
        </Link>

        <nav className="flex items-center gap-2 text-xs font-semibold sm:gap-3">
          {session?.organisation.type === "contractor" && (
            <Link href="/contractor" className="rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800">
              Contractor workspace
            </Link>
          )}
          {session?.organisation.type === "supplier" && (
            <Link href="/supplier" className="rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800">
              Supplier inbox
            </Link>
          )}
          {session?.user.role === "platform_operator" && (
            <Link href="/operator/suppliers" className="rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800">
              Supplier review
            </Link>
          )}
          {session ? (
            <button
              type="button"
              onClick={signOut}
              className="rounded-lg border border-slate-600 px-3 py-2 text-white hover:bg-slate-800"
            >
              Sign out
            </button>
          ) : (
            <>
              <Link href="/login" className="rounded-lg px-3 py-2 text-slate-200 hover:bg-slate-800">
                Sign in
              </Link>
              <Link href="/register" className="rounded-lg bg-[#D9A94A] px-3 py-2 font-bold text-[#12233F] hover:bg-amber-300">
                Register
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
