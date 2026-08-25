"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, get } from "@/lib/api";

type Me = { username: string; role: string; full_name: string | null };

export default function UserMenu() {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const onLoginPage = pathname.startsWith("/login");

  useEffect(() => {
    if (onLoginPage) return;
    get<Me>("/auth/me")
      .then(setMe)
      .catch(() => setMe(null));
  }, [onLoginPage]);

  if (onLoginPage || !me) {
    return (
      <Link
        href="/login"
        className="rounded-sm bg-biro px-3 py-1.5 font-display text-[12px] font-semibold uppercase tracking-[0.12em] text-paper hover:bg-ink"
      >
        Log in
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="hidden font-mono text-xs text-ink sm:inline">
        {me.full_name || me.username}
        <span className="ml-2 inline-block border border-kraft px-1 py-px font-mono text-[9px] uppercase tracking-[0.14em] text-pencil">
          {me.role}
        </span>
      </span>
      <button
        onClick={() => {
          clearToken();
          router.push("/login");
        }}
        className="font-mono text-xs text-pencil underline decoration-kraft underline-offset-4 hover:text-stamp hover:decoration-stamp"
      >
        Log out
      </button>
    </div>
  );
}
