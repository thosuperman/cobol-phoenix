import Link from "next/link";
import { SITE } from "@/lib/site";
import { cx as cn } from "@/lib/cx";

export const LEGAL_LINKS = [
  { href: "/terms", label: "Terms" },
  { href: "/privacy", label: "Privacy" },
  { href: "/disclaimer", label: "Disclaimer" },
];

/** Small row of legal and source links, used in the landing footer, the app sidebar and the legal pages. */
export function LegalLinks({ className }: { className?: string }) {
  return (
    <nav aria-label="Legal" className={cn("flex flex-wrap items-center gap-x-3 gap-y-1", className)}>
      {LEGAL_LINKS.map((l) => (
        <Link key={l.href} href={l.href} className="hover:text-fog-100">
          {l.label}
        </Link>
      ))}
      <a href={SITE.repoUrl} target="_blank" rel="noopener noreferrer" className="hover:text-fog-100">
        Source
      </a>
    </nav>
  );
}
