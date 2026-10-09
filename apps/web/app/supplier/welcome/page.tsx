"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, AuthSession } from "../../../lib/api";

export default function SupplierWelcomePage() {
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    api.getMe().then((s) => setSession(s)).catch(() => {});
  }, []);

  return (
    <div className="max-w-2xl mx-auto space-y-8 py-10 px-4 text-center">
      {/* Celebration Icon */}
      <div className="w-20 h-20 bg-emerald-100 text-emerald-700 rounded-3xl mx-auto flex items-center justify-center text-4xl shadow-inner border border-emerald-200">
        🎉
      </div>

      <div className="space-y-3">
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
          <span>✓ Profile Active in Match Engine</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-serif font-bold text-[#12233F]">
          Welcome to BoQPro, {session?.organisation.legal_name || "Partner"}!
        </h1>
        <p className="text-sm sm:text-base text-slate-600 max-w-lg mx-auto leading-relaxed">
          Your company is now registered as a verified supplier. When tendering contractors broadcast Requests for Quotation (RFQs) matching your trade categories, you will receive instant notifications.
        </p>
      </div>

      {/* How it works for suppliers */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 text-left shadow-sm space-y-4">
        <h3 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-2">
          What happens next?
        </h3>

        <div className="space-y-4 text-xs">
          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 rounded-lg bg-emerald-100 text-emerald-800 font-bold flex items-center justify-center shrink-0 text-xs">
              1
            </div>
            <div>
              <strong className="text-slate-900 block font-semibold">Tendering Contractors Broadcast RFQs</strong>
              <p className="text-slate-500 mt-0.5">
                Contractors upload tender BoQs and request competitive pricing on line items in your province.
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 rounded-lg bg-emerald-100 text-emerald-800 font-bold flex items-center justify-center shrink-0 text-xs">
              2
            </div>
            <div>
              <strong className="text-slate-900 block font-semibold">Instant Mobile Alert</strong>
              <p className="text-slate-500 mt-0.5">
                You receive an urgent notification via WhatsApp and email containing required quantities, units, and response deadlines.
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="w-6 h-6 rounded-lg bg-emerald-100 text-emerald-800 font-bold flex items-center justify-center shrink-0 text-xs">
              3
            </div>
            <div>
              <strong className="text-slate-900 block font-semibold">60-Second 1-Click Submission</strong>
              <p className="text-slate-500 mt-0.5">
                Tap the secure link directly on your phone to submit your unit rate. No desktop login required.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
        <Link
          href="/supplier"
          className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition"
        >
          Go to Supplier Dashboard &rarr;
        </Link>
        <Link
          href="/supplier/profile"
          className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-bold text-xs transition"
        >
          View / Edit Trade Categories
        </Link>
      </div>
    </div>
  );
}
