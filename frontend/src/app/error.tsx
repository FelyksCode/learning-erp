"use client";

import { useEffect } from "react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="doc-panel border-l-4 border-l-stamp p-5">
      <p className="font-display text-sm font-semibold uppercase tracking-[0.12em] text-stamp">
        The books won&rsquo;t open
      </p>
      <p className="mt-2 text-sm text-ink">
        Can&rsquo;t load shop data ({error.message}). Start the backend on localhost:8000, then try again.
      </p>
      <button
        onClick={reset}
        className="mt-4 rounded-sm bg-biro px-4 py-2 font-display text-[13px] font-semibold uppercase tracking-[0.12em] text-paper hover:bg-ink"
      >
        Try again
      </button>
    </div>
  );
}
