"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, Ban, Boxes, FileCode2, FlaskConical, Gauge, GitBranch, Link2, Network, Sparkles } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { sourceHref, useProject } from "@/components/project-context";
import { bandTone } from "@/components/status";
import { Badge, Card, CardHeader, EmptyState, PageLoading, StatTile } from "@/components/ui";

const BAND_COLOR: Record<string, string> = { Low: "#34d399", Medium: "#fbbf24", High: "#ff8a1f", "Very High": "#fb7185" };

export default function OverviewPage() {
  const { id, analysis } = useProject();
  if (!analysis) return <PageLoading />;
  const o = analysis.overview;
  const progs = [...analysis.programs].sort((a, b) => b.metrics.score - a.metrics.score);
  const unsup = Object.entries(o.unsupported_by_construct).map(([k, v]) => ({ construct: k, count: v }));
  const errs = analysis.diagnostics.filter((d) => d.severity === "error");
  const warns = analysis.diagnostics.filter((d) => d.severity === "warning");
  const generatable = analysis.programs.filter((p) => p.unsupported === 0);
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        <StatTile label="Programs" value={o.programs} icon={<FileCode2 className="h-4 w-4" />} />
        <StatTile label="Copybooks" value={o.copybooks} icon={<Boxes className="h-4 w-4" />} />
        <StatTile label="Source lines" value={o.source_lines.toLocaleString()} />
        <StatTile label="Dependencies" value={o.dependencies} hint={`${o.call_edges} CALL · ${o.copy_edges} COPY`} icon={<Link2 className="h-4 w-4" />} />
        <StatTile label="Business rules" value={o.business_rules} accent icon={<GitBranch className="h-4 w-4" />} />
        <StatTile label="Unsupported" value={o.unsupported_constructs} hint="reported, never ignored" icon={<Ban className="h-4 w-4" />} />
        <StatTile label="Complexity" value={<span className={bandTone(o.complexity_band)}>{o.complexity_band}</span>} hint={`score ${o.complexity_score}`} icon={<Gauge className="h-4 w-4" />} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { href: `/projects/${id}/rules`, icon: GitBranch, t: "Explore business rules", b: `${o.business_rules} rules with source evidence` },
          { href: `/projects/${id}/generate`, icon: Sparkles, t: "Generate a Python API", b: `${generatable.length} of ${o.programs} programs fully translatable` },
          { href: `/projects/${id}/verify`, icon: FlaskConical, t: "Prove it against GnuCOBOL", b: "Differential tests + mutation analysis" },
        ].map((c) => (
          <Link key={c.t} href={c.href} className="group flex items-center gap-4 rounded-xl border border-ink-600/70 bg-ink-850/70 p-4 transition hover:border-phoenix-500/40">
            <div className="rounded-lg border border-ink-600 bg-ink-800 p-2.5 text-phoenix-400">
              <c.icon className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="font-medium text-fog-50">{c.t}</div>
              <div className="text-xs text-fog-400">{c.b}</div>
            </div>
            <ArrowRight className="h-4 w-4 text-fog-500 transition group-hover:translate-x-0.5 group-hover:text-phoenix-400" />
          </Link>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Programs" subtitle="Complexity score per program (documented heuristic)" icon={<FileCode2 className="h-4 w-4" />} />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-700 text-left text-[11px] uppercase tracking-wider text-fog-500">
                  <th className="px-5 py-2.5 font-medium">Program</th>
                  <th className="px-3 py-2.5 font-medium">Kind</th>
                  <th className="px-3 py-2.5 text-right font-medium">Stmts</th>
                  <th className="px-3 py-2.5 text-right font-medium">Decisions</th>
                  <th className="px-3 py-2.5 text-right font-medium">Rules</th>
                  <th className="px-3 py-2.5 text-right font-medium">Unsupported</th>
                  <th className="px-5 py-2.5 font-medium">Complexity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-700/70">
                {progs.map((p) => (
                  <tr key={p.program_id} className="hover:bg-ink-800/50">
                    <td className="px-5 py-2.5">
                      <Link href={sourceHref(id, p.file, p.line_start)} className="font-mono text-fog-50 hover:text-phoenix-300">
                        {p.program_id}
                      </Link>
                      <div className="text-[11px] text-fog-500">{p.file}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <Badge tone={p.kind === "subprogram" ? "violet" : "neutral"}>{p.kind}</Badge>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{p.metrics.statements}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{p.metrics.decision_points}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{p.rules}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{p.unsupported > 0 ? <span className="text-violet-300">{p.unsupported}</span> : <span className="text-fog-500">0</span>}</td>
                    <td className="px-5 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-ink-700">
                          <div className="h-full rounded-full" style={{ width: `${Math.min(100, (p.metrics.score / Math.max(...progs.map((x) => x.metrics.score))) * 100)}%`, background: BAND_COLOR[p.metrics.band] }} />
                        </div>
                        <span className={`text-xs ${bandTone(p.metrics.band)}`}>{p.metrics.band}</span>
                        <span className="text-[11px] tabular-nums text-fog-500">{p.metrics.score}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-ink-700 px-5 py-3 font-mono text-[11px] text-fog-500">
            score = statements×1 + decision points×3 + paragraphs×2 + CALLs×4 + unsupported×10 + data items×0.25 · bands &lt;150 Low, &lt;400 Medium, &lt;900 High
          </div>
        </Card>

        <Card>
          <CardHeader title="Unsupported constructs" subtitle="Reported with file and line — the generator raises UnsupportedConstruct if executed" icon={<Ban className="h-4 w-4" />} />
          {unsup.length === 0 ? (
            <div className="p-5">
              <EmptyState title="Everything is inside the supported subset" body="No unsupported COBOL constructs were found in this project." icon={<Network className="h-8 w-8" />} />
            </div>
          ) : (
            <div className="p-4">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={unsup} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <CartesianGrid horizontal={false} stroke="#262d39" />
                    <XAxis type="number" stroke="#6c7584" fontSize={11} allowDecimals={false} />
                    <YAxis type="category" dataKey="construct" stroke="#98a1af" fontSize={11} width={110} />
                    <Tooltip cursor={{ fill: "#1b2029" }} contentStyle={{ background: "#0f1218", border: "1px solid #343d4c", borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {unsup.map((u) => (
                        <Cell key={u.construct} fill="#a78bfa" />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 max-h-56 space-y-1 overflow-y-auto">
                {analysis.unsupported.slice(0, 80).map((u, i) => (
                  <Link key={i} href={sourceHref(id, u.file, u.line, u.end_line)} className="flex items-start gap-2 rounded-md px-2 py-1 text-xs hover:bg-ink-800">
                    <Badge tone="violet">{u.construct}</Badge>
                    <span className="font-mono text-fog-400">
                      {u.file}:{u.line}
                    </span>
                    <span className="truncate text-fog-500">{u.reason}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      <Card>
        <CardHeader title="Parser diagnostics" subtitle={`${errs.length} errors · ${warns.length} warnings`} icon={<AlertTriangle className="h-4 w-4" />} />
        {analysis.diagnostics.length === 0 ? (
          <div className="px-5 py-4 text-sm text-fog-400">No parser errors or warnings. Every source file was parsed into the intermediate representation.</div>
        ) : (
          <div className="max-h-72 divide-y divide-ink-700/60 overflow-y-auto">
            {analysis.diagnostics.slice(0, 200).map((d, i) => (
              <Link key={i} href={sourceHref(id, d.file, d.line)} className="flex items-center gap-3 px-5 py-2 text-xs hover:bg-ink-800/60">
                <Badge tone={d.severity === "error" ? "red" : "amber"}>{d.severity}</Badge>
                <span className="font-mono text-fog-500">{d.code}</span>
                <span className="font-mono text-fog-400">
                  {d.file}:{d.line}
                </span>
                <span className="text-fog-300">{d.message}</span>
              </Link>
            ))}
          </div>
        )}
      </Card>

      {(analysis.project.import_report.skipped_count ?? 0) > 0 && (
        <Card>
          <CardHeader title="Import report" subtitle={`${analysis.project.import_report.stored} files stored · ${analysis.project.import_report.skipped_count} skipped`} />
          <div className="max-h-48 overflow-y-auto px-5 py-3 font-mono text-xs text-fog-500">
            {analysis.project.import_report.skipped?.map((s, i) => (
              <div key={i}>
                {s.path} — {s.reason}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
