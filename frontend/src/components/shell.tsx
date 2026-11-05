"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Boxes, Cpu, FolderUp, LayoutDashboard, Menu, X } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { Wordmark } from "./logo";
import { cn } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/import", label: "Import project", icon: FolderUp },
];

export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const projects = useApi(() => api.projects(), [path.startsWith("/projects") ? "" : path]);
  const health = useApi(() => api.health(), []);
  const sidebar = (
    <nav className="flex h-full flex-col">
      <Link href="/" className="px-5 py-5">
        <Wordmark />
      </Link>
      <div className="space-y-0.5 px-3">
        {NAV.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            onClick={() => setOpen(false)}
            className={cn("flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition", path === n.href ? "bg-ink-700 text-fog-50" : "text-fog-400 hover:bg-ink-800 hover:text-fog-100")}
          >
            <n.icon className="h-4 w-4" />
            {n.label}
          </Link>
        ))}
      </div>
      <div className="mt-6 px-5 text-[10px] font-semibold uppercase tracking-[0.18em] text-fog-500">Projects</div>
      <div className="mt-2 flex-1 space-y-0.5 overflow-y-auto px-3">
        {projects.data?.length === 0 && <div className="px-3 py-2 text-xs text-fog-500">No projects yet</div>}
        {projects.data?.map((p) => (
          <Link
            key={p.id}
            href={`/projects/${p.id}`}
            onClick={() => setOpen(false)}
            className={cn("flex items-center gap-2.5 truncate rounded-lg px-3 py-1.5 text-[13px] transition", path.startsWith(`/projects/${p.id}`) ? "bg-ink-700 text-fog-50" : "text-fog-400 hover:bg-ink-800 hover:text-fog-100")}
          >
            <Boxes className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{p.name}</span>
          </Link>
        ))}
      </div>
      <div className="border-t border-ink-700 px-5 py-4 text-xs">
        <div className="flex items-center gap-2 text-fog-400">
          <Cpu className="h-3.5 w-3.5" /> COBOL sandbox
        </div>
        {health.data ? (
          <div className="mt-1.5 flex items-start gap-2">
            <span className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", health.data.executor.available ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-amber-400")} />
            <span className="text-fog-300">
              {health.data.executor.available ? "GnuCOBOL ready" : "Unavailable"}
              <span className="block text-[10.5px] text-fog-500">{health.data.executor.detail}</span>
            </span>
          </div>
        ) : (
          <div className="mt-1.5 text-fog-500">{health.error ? "backend unreachable" : "checking…"}</div>
        )}
        {health.data && <div className="mt-2 text-[10.5px] text-fog-500">AI explanations: {health.data.llm.provider}</div>}
      </div>
    </nav>
  );
  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-ink-700 bg-ink-900/95 lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-ink-700 bg-ink-900">{sidebar}</aside>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-ink-700 bg-ink-950/80 px-4 py-3 backdrop-blur lg:hidden">
          <button onClick={() => setOpen(!open)} className="text-fog-300" aria-label="Toggle navigation">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <Wordmark />
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
