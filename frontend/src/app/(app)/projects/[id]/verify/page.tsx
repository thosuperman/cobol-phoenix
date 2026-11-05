"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Bug, CheckCircle2, Cpu, FlaskConical, Gauge, PlayCircle, ShieldAlert, Skull, Terminal, XCircle } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FixturesEditor } from "@/components/fixtures-editor";
import { sourceHref, useProject } from "@/components/project-context";
import { STATUS_META, StatusBadge } from "@/components/status";
import { Badge, Button, Card, CardHeader, Chip, EmptyState, ErrorBox, PageLoading, PageTitle, Spinner, StatTile, cn } from "@/components/ui";
import { api, type CaseResult, type MutationResult, type Report, type Run } from "@/lib/api";
import { fmtDate, useApi, usePoll } from "@/lib/use-api";

function VerifyInner() {
  const { id } = useProject();
  const params = useSearchParams();
  const router = useRouter();
  const gens = useApi(() => api.generations(id), [id]);
  const runs = useApi(() => api.runs(id), [id]);
  const [gen, setGen] = useState<string>(params.get("gen") ?? "");
  const [withMut, setWithMut] = useState(true);
  const [starting, setStarting] = useState(false);
  const [err, setErr] = useState<unknown>();
  const runId = params.get("run") ?? undefined;

  useEffect(() => {
    if (!gen && gens.data?.length) setGen((gens.data.find((g) => !g.mutation_id) ?? gens.data[0]).id);
  }, [gens.data, gen]);
  useEffect(() => {
    if (!runId && runs.data?.length && !params.get("gen")) router.replace(`/projects/${id}/verify?run=${runs.data[0].id}`);
  }, [runs.data, runId, id, router, params]);

  const selectedGen = gens.data?.find((g) => g.id === gen);
  async function start() {
    setStarting(true);
    setErr(undefined);
    try {
      const r = await api.verify(gen, withMut && !selectedGen?.mutation_id);
      runs.reload();
      router.push(`/projects/${id}/verify?run=${r.id}`);
    } catch (e) {
      setErr(e);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageTitle eyebrow="Act IV · The proof" title="Differential verification" subtitle="The original COBOL runs in a sandboxed GnuCOBOL container; the generated Python runs in a subprocess. Same inputs, field-by-field comparison. No result is ever simulated." />
      <Card>
        <div className="flex flex-wrap items-end gap-4 p-4">
          <label className="min-w-72 flex-1 text-xs text-fog-400">
            Generated service
            <select value={gen} onChange={(e) => setGen(e.target.value)} className="mt-1 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-fog-100">
              {!gens.data?.length && <option value="">— generate a service first —</option>}
              {gens.data?.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.entry} · {g.name} {g.mutation_id ? `· FAULT: ${g.mutation_detail}` : ""} · {fmtDate(g.created_at)}
                </option>
              ))}
            </select>
          </label>
          <label className={cn("flex items-center gap-2 pb-2 text-sm", selectedGen?.mutation_id ? "text-fog-500" : "text-fog-200")}>
            <input type="checkbox" className="accent-phoenix-500" checked={withMut && !selectedGen?.mutation_id} disabled={!!selectedGen?.mutation_id} onChange={(e) => setWithMut(e.target.checked)} />
            Include mutation analysis (test-suite strength)
          </label>
          <Button variant="primary" onClick={start} loading={starting} disabled={!gen}>
            <PlayCircle className="h-4 w-4" /> Run verification
          </Button>
        </div>
        {selectedGen?.mutation_id && (
          <div className="flex items-center gap-2 border-t border-rose-500/20 bg-rose-500/5 px-4 py-2.5 text-xs text-rose-200">
            <Bug className="h-3.5 w-3.5" /> This build contains a deliberately injected fault ({selectedGen.mutation_detail}). The verifier is expected to report FAILED cases.
          </div>
        )}
      </Card>
      <FixturesEditor projectId={id} />
      {err ? <ErrorBox error={err} /> : null}
      {!gens.loading && !gens.data?.length && <EmptyState title="No generated service yet" body="Generate a Python service first, then come back to prove it." action={<Link href={`/projects/${id}/generate`} className="text-phoenix-300 hover:underline">Go to Generate →</Link>} />}
      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="h-fit">
          <CardHeader title="Runs" subtitle="newest first" />
          <div className="max-h-[70vh] divide-y divide-ink-700/70 overflow-y-auto">
            {runs.data?.length === 0 && <div className="p-4 text-xs text-fog-500">No runs yet.</div>}
            {runs.data?.map((r) => (
              <Link key={r.id} href={`/projects/${id}/verify?run=${r.id}`} className={cn("block px-4 py-3 text-xs transition", runId === r.id ? "bg-ink-700/60" : "hover:bg-ink-800/60")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-sm text-fog-100">{r.entry}</span>
                  {r.status === "completed" ? <StatusBadge status={(r.summary.failed ?? 0) > 0 ? "FAILED" : (r.summary.verified ?? 0) > 0 ? "VERIFIED" : "NOT_VERIFIABLE"} compact /> : <Badge tone={r.status === "error" ? "red" : "amber"}>{r.status}</Badge>}
                </div>
                <div className="mt-1 flex justify-between text-fog-500">
                  <span>{fmtDate(r.created_at)}</span>
                  <span className="font-mono">
                    {r.summary.verified ?? 0}/{r.summary.total ?? 0}
                  </span>
                </div>
                {r.mutation_id && <div className="mt-1 text-rose-300/80">fault: {r.mutation_detail}</div>}
              </Link>
            ))}
          </div>
        </Card>
        <div className="min-w-0">{runId ? <RunView key={runId} rid={runId} onDone={runs.reload} /> : <EmptyState title="Select or start a run" icon={<FlaskConical className="h-8 w-8" />} />}</div>
      </div>
    </div>
  );
}

function RunView({ rid, onDone }: { rid: string; onDone: () => void }) {
  const { id } = useProject();
  const run = useApi(() => api.run(rid), [rid]);
  const active = run.data?.status === "queued" || run.data?.status === "running";
  const [wasActive, setWasActive] = useState(false);
  usePoll(run.reload, 1200, active);
  useEffect(() => {
    if (active) setWasActive(true);
    else if (wasActive) onDone();
  }, [active, wasActive, onDone]);
  if (run.error) return <ErrorBox error={run.error} onRetry={run.reload} />;
  if (!run.data) return <PageLoading />;
  const r = run.data;
  if (active)
    return (
      <Card className="grid-bg p-10 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-phoenix-500/40 bg-phoenix-500/10">
          <Cpu className="animate-ember h-6 w-6 text-phoenix-400" />
        </div>
        <div className="font-medium text-fog-50">Verification running</div>
        <div className="mt-1 font-mono text-xs text-fog-400">{r.progress || r.status}</div>
        <div className="mt-4 flex justify-center">
          <Spinner label="compiling with cobc, executing both runtimes, comparing fields" />
        </div>
      </Card>
    );
  if (r.status === "error") return <ErrorBox error={r.error ?? "verification failed"} />;
  if (!r.report) return null;
  return <ReportView projectId={id} run={r} report={r.report} mutation={r.mutation ?? null} />;
}

function ReportView({ projectId, run, report, mutation }: { projectId: string; run: Run; report: Report; mutation: MutationResult | null }) {
  const s = report.summary;
  const [status, setStatus] = useState<string>(s.failed ? "FAILED" : "");
  const [kind, setKind] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  const cases = report.cases.filter((c) => (!status || c.status === status) && (!kind || c.kind === kind));
  const current = report.cases.find((c) => c.id === sel) ?? cases[0];
  const chart = Object.entries(s.by_kind).map(([k, v]) => ({ kind: k, ...v }));
  const statuses = ["VERIFIED", "FAILED", "NOT_VERIFIABLE", "UNSUPPORTED"] as const;
  const ok = s.failed === 0 && s.verified > 0 && s.not_verifiable === 0;
  return (
    <div className="space-y-5">
      <div className={cn("rounded-xl border px-5 py-4", ok ? "border-emerald-500/30 bg-emerald-500/5" : s.failed ? "border-rose-500/30 bg-rose-500/5" : "border-amber-400/30 bg-amber-400/5")}>
        <div className="flex flex-wrap items-center gap-2">
          {ok ? <CheckCircle2 className="h-5 w-5 text-emerald-400" /> : s.failed ? <XCircle className="h-5 w-5 text-rose-400" /> : <ShieldAlert className="h-5 w-5 text-amber-300" />}
          <span className="font-semibold text-fog-50">{report.entry}</span>
          {report.mutation && (
            <Badge tone="red">
              <Bug className="h-3 w-3" /> injected fault: {report.mutation.detail}
            </Badge>
          )}
          <span className="text-xs text-fog-500">
            {fmtDate(run.finished_at)} · {report.duration_s}s · fixed clock {report.fixed_datetime}
          </span>
        </div>
        <p className="mt-2 text-sm text-fog-200">{report.claim}</p>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-fog-500">
          <span>executor: {report.executor.name}</span>
          <span>{report.executor.cobc_version || report.executor.error}</span>
          <span>compile: {report.compile.ok ? "ok" : "failed"}</span>
          <span>harness: {report.mode}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 2xl:grid-cols-6">
        <StatTile label="Cases" value={s.total} />
        <StatTile label="Verified" value={<span className="text-emerald-300">{s.verified}</span>} accent={ok} />
        <StatTile label="Failed" value={<span className={s.failed ? "text-rose-300" : ""}>{s.failed}</span>} />
        <StatTile label="Not verifiable" value={s.not_verifiable} />
        <StatTile label="Unsupported" value={s.unsupported} />
        <StatTile label="Statement coverage" value={`${s.coverage_pct}%`} hint={`${s.statements_executed}/${s.statements_total} COBOL statements`} icon={<Gauge className="h-4 w-4" />} />
      </div>

      <div className="grid gap-5 2xl:grid-cols-2">
        <Card>
          <CardHeader title="Results by case kind" subtitle="fixture · boundary · edge · seeded random" />
          <div className="h-56 p-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart} margin={{ left: -10 }}>
                <CartesianGrid vertical={false} stroke="#262d39" />
                <XAxis dataKey="kind" stroke="#98a1af" fontSize={11} />
                <YAxis stroke="#6c7584" fontSize={11} allowDecimals={false} />
                <Tooltip cursor={{ fill: "#1b2029" }} contentStyle={{ background: "#0f1218", border: "1px solid #343d4c", borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {statuses.map((st) => (
                  <Bar key={st} dataKey={st} stackId="a" fill={STATUS_META[st].dot} radius={st === "VERIFIED" ? [0, 0, 0, 0] : undefined} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        {mutation ? (
          <MutationCard m={mutation} />
        ) : (
          <Card>
            <CardHeader title="Mutation analysis" subtitle="Not included in this run" icon={<Skull className="h-4 w-4" />} />
            <div className="p-5 text-sm text-fog-400">Re-run with “Include mutation analysis” to measure how many single-fault variants of the generated code the suite detects.</div>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader
          title="Cases"
          subtitle={`${cases.length} shown`}
          icon={<Terminal className="h-4 w-4" />}
          actions={
            <div className="flex flex-wrap gap-1.5">
              <Chip active={!status} onClick={() => setStatus("")}>
                all
              </Chip>
              {statuses.map((st) => (
                <Chip key={st} active={status === st} onClick={() => setStatus(status === st ? "" : st)}>
                  <span style={{ color: STATUS_META[st].dot }}>●</span> {st.toLowerCase().replace("_", " ")}
                </Chip>
              ))}
              <select value={kind} onChange={(e) => setKind(e.target.value)} className="rounded-md border border-ink-600 bg-ink-900 px-2 py-0.5 text-[11px] text-fog-200">
                <option value="">all kinds</option>
                {Object.keys(s.by_kind).map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
            </div>
          }
        />
        <div className="grid xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.4fr)]">
          <div className="max-h-[640px] divide-y divide-ink-700/60 overflow-y-auto border-b border-ink-700 xl:border-r xl:border-b-0">
            {cases.length === 0 && <div className="p-4 text-xs text-fog-500">No cases match.</div>}
            {cases.map((c) => (
              <button key={c.id} onClick={() => setSel(c.id)} className={cn("block w-full px-4 py-2.5 text-left text-xs transition", current?.id === c.id ? "bg-ink-700/60" : "hover:bg-ink-800/60")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-fog-100">{c.id}</span>
                  <StatusBadge status={c.status} compact />
                </div>
                <div className="mt-0.5 truncate text-fog-500">{c.description}</div>
              </button>
            ))}
          </div>
          <div className="min-w-0">{current ? <CaseDetail projectId={projectId} c={current} mode={report.mode} /> : null}</div>
        </div>
      </Card>
    </div>
  );
}

function CaseDetail({ projectId, c, mode }: { projectId: string; c: CaseResult; mode: string }) {
  const cob = c.cobol?.stdout ?? "";
  const py = c.python.stdout;
  const inputs = Object.entries(c.inputs).flatMap(([p, f]) => Object.entries(f).map(([k, v]) => ({ p, k, v })));
  const lines = useMemo(() => {
    const a = cob.split("\n");
    const b = py.split("\n");
    return Array.from({ length: Math.max(a.length, b.length) }, (_, i) => ({ a: a[i] ?? "", b: b[i] ?? "", diff: (a[i] ?? "") !== (b[i] ?? "") }));
  }, [cob, py]);
  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm text-fog-50">{c.id}</span>
        <StatusBadge status={c.status} />
        <Badge>{c.kind}</Badge>
        {c.cobol && <span className="text-[11px] text-fog-500">GnuCOBOL rc={String(c.cobol.rc)} · {c.cobol.duration_ms} ms</span>}
      </div>
      <p className="text-xs text-fog-400">{c.description}</p>
      {c.note && <p className="rounded-md border border-ink-600 bg-ink-900 px-3 py-2 text-xs text-amber-200">{c.note}</p>}
      {c.diffs.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-rose-500/30">
          <table className="w-full text-xs">
            <thead className="bg-rose-500/10 text-left text-[10.5px] uppercase tracking-wider text-rose-200">
              <tr>
                <th className="px-3 py-2">Field</th>
                <th className="px-3 py-2">GnuCOBOL</th>
                <th className="px-3 py-2">Python</th>
                <th className="px-3 py-2">Δ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {c.diffs.map((d, i) => (
                <tr key={i}>
                  <td className="px-3 py-2 font-mono text-fog-100">
                    {d.field}
                    {d.loc && (
                      <Link href={sourceHref(projectId, d.loc.split(":")[0], Number(d.loc.split(":")[1]))} className="block text-[10px] text-phoenix-300 hover:underline">
                        {d.loc}
                      </Link>
                    )}
                  </td>
                  <td className="whitespace-pre px-3 py-2 font-mono text-emerald-200">{d.cobol_value ?? (d.cobol ?? "").trimEnd()}</td>
                  <td className="whitespace-pre px-3 py-2 font-mono text-rose-200">{d.python_value ?? (d.python ?? "").trimEnd()}</td>
                  <td className="px-3 py-2 font-mono text-fog-300">{d.delta ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {inputs.length > 0 && (
        <details className="rounded-lg border border-ink-600 bg-ink-900">
          <summary className="cursor-pointer px-3 py-2 text-xs text-fog-300">Inputs ({inputs.length} fields set; all others INITIALIZEd)</summary>
          <div className="grid gap-x-4 gap-y-0.5 px-3 pb-3 font-mono text-[11px] sm:grid-cols-2">
            {inputs.map((x, i) => (
              <div key={i} className="truncate">
                <span className="text-fog-500">{x.k}</span> = <span className="text-sky-200">{x.v || "SPACES"}</span>
              </div>
            ))}
          </div>
        </details>
      )}
      <div>
        <div className="mb-1.5 flex items-center justify-between text-[11px] uppercase tracking-wider text-fog-500">
          <span>Raw output — {mode === "harness" ? "USING parameters after CALL, one line each" : "stdout"}</span>
          <span>{lines.filter((l) => l.diff).length} differing lines</span>
        </div>
        <div className="grid gap-2 lg:grid-cols-2">
          {[
            { t: "GnuCOBOL (original)", key: "a" as const, tone: "text-emerald-300" },
            { t: "Python (generated)", key: "b" as const, tone: "text-phoenix-300" },
          ].map((side) => (
            <div key={side.t} className="min-w-0">
              <div className={`mb-1 text-[11px] font-medium ${side.tone}`}>{side.t}</div>
              <pre className="max-h-72 overflow-auto rounded-lg border border-ink-600 bg-ink-950 p-2 font-mono text-[11px] leading-5">
                {c.cobol === null && side.key === "a" ? (
                  <span className="text-amber-200">not executed</span>
                ) : (
                  lines.map((l, i) => (
                    <div key={i} className={cn("whitespace-pre", l.diff && "bg-rose-500/15 text-rose-100")}>
                      {l[side.key] || " "}
                    </div>
                  ))
                )}
              </pre>
            </div>
          ))}
        </div>
      </div>
      {c.python.error && <pre className="overflow-auto rounded-lg border border-violet-500/30 bg-violet-500/5 p-2 font-mono text-[11px] text-violet-200">{c.python.error}</pre>}
      <div className="text-[11px] text-fog-500">Executed {c.executed.length} COBOL statements (via Python line tracing mapped through traceability.json).</div>
    </div>
  );
}

function MutationCard({ m }: { m: MutationResult }) {
  const [show, setShow] = useState<"survived" | "all">("survived");
  const list = m.mutants.filter((x) => show === "all" || x.status !== "killed");
  return (
    <Card>
      <CardHeader title="Mutation analysis" subtitle={`reference: ${m.reference === "gnucobol" ? "GnuCOBOL outputs" : "generated Python baseline"}`} icon={<Skull className="h-4 w-4" />} actions={<Chip active={show === "all"} onClick={() => setShow(show === "all" ? "survived" : "all")}>{show === "all" ? "all mutants" : "survivors only"}</Chip>} />
      <div className="flex items-center gap-5 px-5 pt-4">
        <div className="text-3xl font-semibold text-phoenix-300 tabular-nums">{m.score_pct}%</div>
        <div className="text-xs text-fog-400">
          {m.killed} of {m.evaluated} single-fault mutants detected by the suite.
          <br />
          Survivors are untested behaviour or equivalent mutants (e.g. ROUNDED on an exact result).
        </div>
      </div>
      <div className="mt-3 max-h-48 divide-y divide-ink-700/60 overflow-y-auto border-t border-ink-700">
        {list.length === 0 && <div className="px-5 py-3 text-xs text-emerald-300">Every mutant was killed.</div>}
        {list.map((x) => (
          <div key={x.id} className="flex items-center gap-3 px-5 py-2 text-xs">
            <Badge tone={x.status === "killed" ? "green" : "amber"}>{x.status}</Badge>
            <span className="truncate text-fog-200">{x.detail}</span>
            <span className="ml-auto shrink-0 font-mono text-fog-500">
              {x.file.split("/").pop()}:{x.line}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <VerifyInner />
    </Suspense>
  );
}
