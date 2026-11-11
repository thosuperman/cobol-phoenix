import Link from "next/link";
import type { ReactNode } from "react";
import { SITE } from "@/lib/site";
import { PhoenixMark, Wordmark } from "./logo";
import { LEGAL_LINKS, LegalLinks } from "./site-footer";
import { cx as cn } from "@/lib/cx";

/** Layout shared by /terms, /privacy and /disclaimer: readable column, in-page contents, plain-words summary. */
export function LegalPage({
  path,
  title,
  intro,
  summary,
  toc,
  children,
}: {
  path: string;
  title: string;
  intro: ReactNode;
  summary: ReactNode[];
  toc: { id: string; title: string }[];
  children: ReactNode;
}) {
  return (
    <div className="relative min-h-screen">
      <div className="grid-bg pointer-events-none absolute inset-x-0 top-0 h-80 [mask-image:linear-gradient(to_bottom,black,transparent)]" />
      <header className="relative z-10 mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
        <Link href="/" aria-label={`${SITE.name} home`}>
          <Wordmark id="phx-g-legal" />
        </Link>
        <Link href="/dashboard" className="rounded-lg border border-ink-500 bg-ink-800/80 px-3 py-1.5 text-sm text-fog-100 hover:bg-ink-700">
          Open workspace
        </Link>
      </header>

      <div className="relative z-10 mx-auto max-w-5xl px-4 pb-16 sm:px-6">
        <nav aria-label="Legal pages" className="mb-8 flex flex-wrap gap-1.5 border-b border-ink-700 pb-3 text-sm">
          {LEGAL_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={l.href === path ? "page" : undefined}
              className={cn("rounded-lg px-3 py-1.5 transition", l.href === path ? "bg-ink-700 text-fog-50" : "text-fog-400 hover:bg-ink-800 hover:text-fog-100")}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-phoenix-400">Last updated {SITE.legalUpdated}</div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-fog-50 sm:text-4xl">{title}</h1>
        <div className="mt-4 max-w-3xl text-[15px] leading-relaxed text-fog-300">{intro}</div>

        <aside className="mt-8 max-w-3xl rounded-xl border border-phoenix-500/25 bg-phoenix-500/[0.06] p-5">
          <div className="text-sm font-semibold text-phoenix-300">In plain words</div>
          <ul className="mt-2.5 space-y-1.5 text-sm leading-relaxed text-fog-100">
            {summary.map((s, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-phoenix-400" />
                <span className="min-w-0">{s}</span>
              </li>
            ))}
          </ul>
        </aside>

        <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_220px]">
          <article className="min-w-0 max-w-3xl space-y-10">{children}</article>
          <nav aria-label="On this page" className="hidden lg:block">
            <div className="sticky top-6">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-fog-500">On this page</div>
              <ol className="mt-3 space-y-1.5 text-[13px]">
                {toc.map((t, i) => (
                  <li key={t.id}>
                    <a href={`#${t.id}`} className="flex gap-2 text-fog-400 hover:text-fog-100">
                      <span className="w-5 shrink-0 text-right font-mono text-fog-500">{i + 1}.</span>
                      <span>{t.title}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          </nav>
        </div>
      </div>

      <footer className="relative z-10 border-t border-ink-700">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-xs text-fog-500 sm:px-6">
          <span className="flex items-center gap-2">
            <PhoenixMark className="h-5 w-5" gradientId="phx-g-legal-footer" /> {SITE.name} · Apache-2.0
          </span>
          <LegalLinks />
        </div>
      </footer>
    </div>
  );
}

export function Section({ id, n, title, children }: { id: string; n: number; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-6">
      <h2 className="flex items-baseline gap-3 text-lg font-semibold text-fog-50">
        <span className="font-mono text-sm text-phoenix-400">{String(n).padStart(2, "0")}</span>
        {title}
      </h2>
      <div className="mt-3 space-y-3 text-[15px] leading-relaxed text-fog-300 [&_a]:text-phoenix-300 [&_a]:underline [&_a]:decoration-phoenix-500/40 [&_a]:underline-offset-2 hover:[&_a]:text-phoenix-200 [&_strong]:font-semibold [&_strong]:text-fog-100">
        {children}
      </div>
    </section>
  );
}

export function List({ items }: { items: ReactNode[] }) {
  return (
    <ul className="space-y-1.5 pl-1">
      {items.map((it, i) => (
        <li key={i} className="flex gap-2.5">
          <span className="mt-[0.6rem] h-1 w-1 shrink-0 rounded-full bg-fog-500" />
          <span className="min-w-0">{it}</span>
        </li>
      ))}
    </ul>
  );
}

/** Two-column table for "what / why / how long" style facts; stacks on narrow screens. */
export function FactTable({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-ink-600">
      <table className="w-full text-left text-sm">
        <thead className="hidden bg-ink-800 text-[11px] uppercase tracking-wider text-fog-500 sm:table-header-group">
          <tr>
            {head.map((h) => (
              <th key={h} className="px-4 py-2.5 font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-700">
          {rows.map((r, i) => (
            <tr key={i} className="block sm:table-row">
              {r.map((c, j) => (
                <td key={j} className={cn("block px-4 align-top sm:table-cell sm:py-3", j === 0 ? "pt-3 font-medium text-fog-100" : "pb-1 text-fog-300 last:pb-3")}>
                  {j > 0 && <span className="mr-1.5 text-[11px] uppercase tracking-wider text-fog-500 sm:hidden">{head[j]}:</span>}
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ContactLinks() {
  return (
    <List
      items={[
        <>
          General questions, requests and privacy inquiries: open an issue at{" "}
          <a href={SITE.contactUrl} target="_blank" rel="noopener noreferrer">
            {SITE.contactUrl.replace("https://", "")}
          </a>
          . Do not include personal details you don&apos;t want to be public in an issue; say you have a privacy request and we will arrange a private channel.
        </>,
        <>
          Security vulnerabilities: report privately through{" "}
          <a href={SITE.securityUrl} target="_blank" rel="noopener noreferrer">
            GitHub private vulnerability reporting
          </a>
          .
        </>,
      ]}
    />
  );
}
