"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function BoQIndexPage() {
  const params = useParams();
  const boqId = (params?.boqId as string) || "";
  const router = useRouter();

  useEffect(() => {
    if (boqId) {
      router.replace(`/contractor/boqs/${boqId}/review`);
    }
  }, [boqId, router]);

  return (
    <div className="p-12 text-center text-xs text-slate-500">
      Redirecting to BoQ Line Items...
    </div>
  );
}

