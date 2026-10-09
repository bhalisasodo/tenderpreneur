import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-5xl flex-col justify-center px-6 py-16">
      <p className="text-sm font-bold uppercase tracking-[0.18em] text-amber-700">BoQPro</p>
      <h1 className="mt-4 max-w-3xl text-4xl font-bold leading-tight text-slate-900 sm:text-6xl">
        Tender quantities and supplier quotes, in one workspace.
      </h1>
      <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
        Contractors can structure Bills of Quantities and manage supplier quotes. Suppliers can apply to receive
        relevant requests; each supplier application is reviewed before marketplace access is activated.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/register?type=contractor"
          className="inline-flex rounded-xl bg-[#12233F] px-6 py-3 font-semibold text-white hover:bg-slate-800"
        >
          Register as a contractor
        </Link>
        <Link
          href="/register?type=supplier"
          className="inline-flex rounded-xl border border-slate-300 bg-white px-6 py-3 font-semibold text-[#12233F] hover:bg-slate-50"
        >
          Apply as a supplier
        </Link>
      </div>
    </main>
  );
}
