"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Activity, ArrowRight, Boxes, CheckCircle2, FileCode2, FlaskConical, GitBranch, Plus, Sparkles, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate, useApi } from "@/lib/use-api";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBox, LinkButton, PageLoading, PageTitle, StatTile } from "@/components/ui";
import { StatusBadge, bandTone } from "@/components/status";

export default function DashboardPage() {
  const router = useRouter();
  const { data, error, loading, reload } = useApi(() => api.dashboard(), []);
  const health = useApi(() => api.health(), []);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<unknown>();

  async function importSample() {
    setImporting(true);
    setImportError(undefined);
    try {
      const p = await api.importSample();
      router.push(`/projects/${p.id}`);
    } catch (e) {
      setImportError(e);
      setImporting(false);
    }
  }

  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return null;
  const t = data.totals;
  return (
    <div className="animate-fade-up">
      <PageTitle
        eyebrow="Workspace"
        title="Modernization dashboard"
        subtitle="Projects, extracted business rules and differential verification results across your workspace."
        actions={
          <>
            <Button onClick={importSample} loading={importing}>
              <Sparkles className="h-4 w-4" /> Import sample
            </Button>
            <LinkButton href="/import" variant="primary">
              <Plus className="h-4 w-4" /> Import COBOL
            </LinkButton>
          </>
        }
      />
      {importError ? <div className="mb-4"><ErrorBox error={importError} /></div> : null}
      {health.data && !health.data.executor.available && (
        <div className="mb-6 rounded-xl border border-amber-400/30 bg-amber-400/5 px-4 py-3 text-sm text-amber-100">
          <strong className="font-semibold">GnuCOBOL sandbox unavailable.</strong> Analysis and generation work normally, but verification runs will report{" "}
          <code className="font-mono text-xs">NOT_VERIFIABLE</code> instead of comparing outputs. {health.data.executor.detail}
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Projects" value={t.projects} icon={<Boxes className="h-4 w-4" />} />
        <StatTile label="COBOL programs" value={t.programs} icon={<FileCode2 className="h-4 w-4" />} />
        <StatTile label="Business rules" value={t.rules} icon={<GitBranch className="h-4 w-4" />} />
        <StatTile label="Generated services" value={t.generations} icon={<Sparkles className="h-4 w-4" />} />
        <StatTile label="Cases verified" value={t.cases_verified} accent icon={<CheckCircle2 className="h-4 w-4" />} hint="identical in GnuCOBOL and Python" />
        <StatTile label="Cases failed" value={t.cases_failed} icon={<XCircle className="h-4 w-4" />} hint="latest runs, excl. injected faults" />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Card>
          <CardHeader title="Projects" subtitle="Imported COBOL code bases" icon={<Boxes className="h-4 w-4" />} />
          {data.projects.length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="No projects yet"
                body="Import the bundled Phoenix Mutual insurance sample to see the full workflow in under a minute, or bring your own COBOL."
                action={
                  <Button variant="primary" onClick={importSample} loading={importing}>
                    <Sparkles className="h-4 w-4" /> Import sample project
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="divide-y divide-ink-700">
              {data.projects.map((p) => (
                <Link key={p.id} href={`/projects/${p.id}`} className="group flex flex-wrap items-center gap-4 px-5 py-4 transition hover:bg-ink-800/60">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-medium text-fog-50">{p.name}</span>
                      <Badge>{p.source_kind}</Badge>
                      {p.license && <Badge tone="blue">{p.license}</Badge>}
                    </div>
                    <div className="mt-1 text-xs text-fog-500">
                      {p.overview ? `${p.overview.programs} programs · ${p.overview.copybooks} copybooks · ${p.overview.source_lines.toLocaleString()} lines · ${p.overview.business_rules} rules` : "not analysed"}
                      {" · "}imported {fmtDate(p.created_at)}
                    </div>
                  </div>
                  {p.overview && (
                    <div className="text-right text-xs">
                      <div className="text-fog-500">complexity</div>
                      <div className={`font-semibold ${bandTone(p.overview.complexity_band)}`}>{p.overview.complexity_band}</div>
                    </div>
                  )}
                  <div className="w-44 text-right text-xs">
                    {p.latest_verification ? (
                      <>
                        <div className="text-fog-500">latest verification · {p.latest_verification.entry}</div>
                        <div className="mt-0.5 font-mono text-emerald-300">
                          {p.latest_verification.verified}/{p.latest_verification.total} verified
                          {p.latest_verification.failed > 0 && <span className="text-rose-300"> · {p.latest_verification.failed} failed</span>}
                        </div>
                      </>
                    ) : (
                      <span className="text-fog-500">no verification yet</span>
                    )}
                  </div>
                  <ArrowRight className="h-4 w-4 text-fog-500 transition group-hover:translate-x-0.5 group-hover:text-phoenix-400" />
                </Link>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Recent verification runs" subtitle="GnuCOBOL vs generated Python" icon={<Activity className="h-4 w-4" />} />
          {data.recent_runs.length === 0 ? (
            <div className="p-5 text-sm text-fog-500">No runs yet. Generate a Python service and start a verification run.</div>
          ) : (
            <div className="divide-y divide-ink-700">
              {data.recent_runs.map((r) => (
                <Link key={r.id} href={`/projects/${r.project_id}/verify?run=${r.id}`} className="block px-5 py-3 hover:bg-ink-800/60">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-sm text-fog-100">{r.entry}</span>
                    {r.status === "completed" ? (
                      <StatusBadge status={(r.summary.failed ?? 0) > 0 ? "FAILED" : (r.summary.verified ?? 0) > 0 ? "VERIFIED" : "NOT_VERIFIABLE"} />
                    ) : (
                      <Badge tone={r.status === "error" ? "red" : "amber"}>{r.status}</Badge>
                    )}
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs text-fog-500">
                    <span className="truncate">
                      {r.project_name}
                      {r.mutation_id && (
                        <span className="text-violet-300">
                          {" "}
                          · <FlaskConical className="inline h-3 w-3" /> injected fault
                        </span>
                      )}
                    </span>
                    <span className="font-mono">
                      {r.summary.verified ?? 0}/{r.summary.total ?? 0}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
