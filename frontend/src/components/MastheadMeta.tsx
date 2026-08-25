"use client";

import { useEffect, useState } from "react";

function formatToday() {
  return new Date()
    .toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })
    .toUpperCase();
}

export default function MastheadMeta() {
  const [today, setToday] = useState<string | null>(null);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setToday(formatToday()));
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <p
      className="hidden font-mono text-[10px] uppercase tracking-[0.18em] text-pencil sm:block"
      suppressHydrationWarning
    >
      {today ?? "\u00A0"}
    </p>
  );
}
