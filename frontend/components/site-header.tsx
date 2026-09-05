import Link from "next/link";
import { ScanSearch } from "lucide-react";

const links = [
  { href: "/analyze", label: "Analyze" },
  { href: "/whatsapp", label: "WhatsApp" },
  { href: "/dashboard", label: "Dashboard" },
];

export function SiteHeader() {
  return (
    <header className="border-b border-line bg-paper/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <span className="grid size-8 place-items-center rounded-lg bg-primary text-white">
            <ScanSearch className="size-5" aria-hidden />
          </span>
          Lumen
        </Link>
        <nav aria-label="Primary" className="flex items-center gap-1 sm:gap-2">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="rounded-full px-3 py-2 text-sm font-medium text-ink-soft transition-colors duration-200 hover:bg-signal/10 hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
