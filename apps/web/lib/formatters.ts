export function formatZAR(minorCents?: number | null): string {
  if (minorCents === undefined || minorCents === null) return "—";
  const rands = minorCents / 100;
  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rands);
}

export function formatDateTime(isoString?: string | null): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-ZA", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return isoString;
  }
}

export function formatTimeRemaining(deadlineIso: string): { text: string; isExpired: boolean; isUrgent: boolean } {
  const deadline = new Date(deadlineIso).getTime();
  const now = Date.now();
  const diffMs = deadline - now;

  if (diffMs <= 0) {
    return { text: "Expired", isExpired: true, isUrgent: false };
  }

  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (diffHours < 24) {
    return {
      text: `${diffHours}h ${diffMins}m remaining`,
      isExpired: false,
      isUrgent: diffHours < 6,
    };
  }

  const diffDays = Math.floor(diffHours / 24);
  return {
    text: `${diffDays}d ${diffHours % 24}h remaining`,
    isExpired: false,
    isUrgent: false,
  };
}
