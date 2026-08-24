"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Dashboard" },
  { href: "/products", label: "Products" },
];

export default function NavTabs() {
  const pathname = usePathname();

  return (
    <nav className="flex items-end gap-1">
      {TABS.map((tab) => {
        const isActive = tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={isActive ? "page" : undefined}
            className={`-mb-[2px] rounded-t-md border border-b-0 border-kraft px-4 pt-1.5 pb-2.5 font-display text-[13px] font-semibold uppercase tracking-[0.12em] transition-colors ${
              isActive
                ? "border-b-paper bg-paper text-ink"
                : "bg-transparent pb-2 text-pencil hover:text-ink"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
