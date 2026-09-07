import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tenderpreneur — BoQ Pricing & Supplier Marketplace",
  description: "BoQ pricing and verified supplier quote marketplace for South African tender contractors.",
};

import Navbar from "../components/Navbar";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-slate-50 text-slate-900 antialiased">
        <Navbar />

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4">
            Tenderpreneur &copy; 2026 — BoQ Pricing &amp; Verified Supplier-Quote Marketplace for South African Tenders.
          </div>
        </footer>
      </body>
    </html>
  );
}
