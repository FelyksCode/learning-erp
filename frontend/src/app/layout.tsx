import type { Metadata } from "next";
import { Barlow_Semi_Condensed, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import MastheadMeta from "@/components/MastheadMeta";
import NavTabs from "@/components/NavTabs";
import UserMenu from "@/components/UserMenu";
import "./globals.css";

const display = Barlow_Semi_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--f-display",
});

const body = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--f-body",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--f-mono",
});

export const metadata: Metadata = {
  title: "The Stock Ledger",
  description: "Shop inventory, restock list and sales notes",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`h-full ${display.variable} ${body.variable} ${mono.variable}`}>
      <body className="min-h-full">
        <header className="border-b-2 border-ink bg-paper">
          <div className="mx-auto max-w-6xl px-4 pt-4 sm:px-6">
            <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 pb-3">
              <Link href="/" className="block leading-none focus-visible:outline-2">
                <span className="font-display text-[22px] font-bold uppercase tracking-[0.06em] text-ink">
                  The Stock Ledger
                </span>
                <span className="mt-1.5 block font-mono text-[10px] uppercase tracking-[0.22em] text-pencil">
                  Inventory · restock · sales
                </span>
              </Link>
              <div className="flex items-center gap-4 pt-1">
                <MastheadMeta />
                <UserMenu />
              </div>
            </div>
            <NavTabs />
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
