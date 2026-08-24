"use client";

import { useCallback, useState } from "react";
import { get, post, type AIInsights } from "@/lib/api";

export default function AdvisorNote({ initial }: { initial: AIInsights }) {
  const [ai, setAi] = useState<AIInsights>(initial);
  const [busy, setBusy] = useState(false);

  const regenerate = useCallback(() => {
    setBusy(true);
    post<AIInsights>("/ai/insights")
      .then(setAi)
      .catch(() => setAi({ enabled: false, reason: "Could not reach the API. Check the backend, then try again." }))
      .finally(() => setBusy(false));
  }, []);

  return (
    <section aria-label="Advisor note" className="doc-panel border-l-4 border-l-biro p-4 sm:p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="eyebrow">Advisor&rsquo;s note</p>
        {ai.enabled && (
          <button
            onClick={regenerate}
            disabled={busy}
            className="rounded-sm border border-ink/30 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink hover:bg-manila disabled:opacity-50"
          >
            {busy ? "Reading the books\u2026" : "Write it again"}
          </button>
        )}
      </div>
      {busy && !ai.insight ? (
        <p className="pt-2 text-sm text-pencil">Going through the restock list…</p>
      ) : ai.enabled && ai.insight ? (
        <p className="whitespace-pre-wrap pt-2 text-sm leading-relaxed text-ink">{ai.insight}</p>
      ) : (
        <p className="pt-2 text-sm text-pencil">{ai.reason ?? "No advisor note available."}</p>
      )}
    </section>
  );
}
