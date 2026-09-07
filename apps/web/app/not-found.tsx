import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-md mx-auto py-16 px-4 text-center space-y-4">
      <div className="w-12 h-12 rounded-2xl bg-blue-100 text-blue-600 font-black text-2xl flex items-center justify-center mx-auto">
        404
      </div>
      <h2 className="text-xl font-bold text-slate-900">Page Not Found</h2>
      <p className="text-xs text-slate-500">
        The requested tender, BoQ, or quote request could not be located.
      </p>
      <div className="pt-2">
        <Link
          href="/"
          className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow transition"
        >
          &larr; Return to Tenderpreneur Home
        </Link>
      </div>
    </div>
  );
}
