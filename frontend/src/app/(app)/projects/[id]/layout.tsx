"use client";

import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Code2, Download, FlaskConical, GitBranch, LayoutGrid, Network, RefreshCw, ScrollText, Sparkles, Trash2 } from "lucide-react";
import { ProjectProvider, useProject } from "@/components/project-context";
import { Badge, Button, ErrorBox, cn } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/use-api";

const TABS = [
  { seg: "", label: "Overview", icon: LayoutGrid },
  { seg: "source", label: "Source", icon: Code2 },
  { seg: "graph", label: "Dependencies", icon: Network },
  { seg: "rules", label: "Business rules", icon: GitBranch },
  { seg: "generate", label: "Generate", icon: Sparkles },
  { seg: "verify", label: "Verify", icon: FlaskConical },
  { seg: "export", label: "Export", icon: Download },
];

function Header() {
  const { id, analysis, error, reload } = useProject();
  const path = usePathname();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const base = `/projects/${id}`;
  const p = analysis?.project;
  async function reanalyze() {
    setBusy(true);
    try {
      await api.analyze(id);
      reload();
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    if (!confirm("Delete this project, its generated services and verification runs?")) return;
    await api.deleteProject(id);
    router.push("/dashboard");
  }
  return (
    <div className="mb-6">
      {error ? <ErrorBox error={error} onRetry={reload} /> : null}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-phoenix-400">Project</div>
          <h1 className="mt-1 truncate text-2xl font-semibold tracking-tight text-fog-50">{p?.name ?? "…"}</h1>
          {p && (
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-fog-500">
              <Badge>{p.source_kind}</Badge>
              {p.license ? <Badge tone="blue">license: {p.license}</Badge> : <Badge tone="amber">no license file detected</Badge>}
              <span className="truncate">{p.source_ref}</span>
              <span>· analysed {fmtDate(p.analyzed_at)}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" onClick={reanalyze} loading={busy} title="Re-run the deterministic analysis">
            <RefreshCw className="h-4 w-4" /> Re-analyse
          </Button>
          <Button variant="ghost" onClick={remove} title="Delete project">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <nav className="mt-5 flex gap-1 overflow-x-auto border-b border-ink-700">
        {TABS.map((t) => {
          const href = t.seg ? `${base}/${t.seg}` : base;
          const active = t.seg ? path.startsWith(href) || (t.seg === "generate" && path.startsWith(`${base}/generations`)) : path === base;
          return (
            <Link key={t.label} href={href} className={cn("-mb-px flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm whitespace-nowrap transition", active ? "border-phoenix-500 text-fog-50" : "border-transparent text-fog-400 hover:text-fog-100")}>
              <t.icon className="h-4 w-4" />
              {t.label}
            </Link>
          );
        })}
        <span className="flex-1" />
        <Link href={`${base}/export`} className="hidden items-center gap-1 px-2 text-xs text-fog-500 hover:text-fog-300 md:flex">
          <ScrollText className="h-3.5 w-3.5" /> reports
        </Link>
      </nav>
    </div>
  );
}

export default function ProjectLayout({ children }: { children: ReactNode }) {
  const { id } = useParams<{ id: string }>();
  return (
    <ProjectProvider id={id}>
      <Header />
      <div className="animate-fade-up">{children}</div>
    </ProjectProvider>
  );
}
