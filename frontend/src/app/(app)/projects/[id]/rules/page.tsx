"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Bot, Calculator, ExternalLink, GitBranch, ListChecks, Search, Split, Table2 } from "lucide-react";
import { CodeViewer } from "@/components/code-viewer";
import { sourceHref, useProject } from "@/components/project-context";
import { STATUS_META, StatusBadge } from "@/components/status";
import { Badge, Button, Card, CardHeader, Chip, EmptyState, ErrorBox, PageLoading, Spinner, cn } from "@/components/ui";
import { api, type Explanation, type Rule } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function RulesPage() {
  const { id, analysis } = useProject();
  const rules = useApi(() => api.rules(id), [id]);
  const [q, setQ] = useState("");
  const [prog, setProg] = useState("");
  const [status, setStatus] = useState("");
  const [sel, setSel] = useState<string | null>(null);

  const list = useMemo(() => {
    const r = rules.data ?? [];
    const ql = q.toLowerCase();
    return r.filter(
      (x) =>
        (!prog || x.program === prog) &&
        (!status || x.verification.status === status) &&
        (!ql || x.name.toLowerCase().includes(ql) || x.description.toLowerCase().includes(ql) || x.inputs.some((i) => i.toLowerCase().includes(ql)) || x.outputs.some((o) => o.toLowerCase().includes(ql))),
    );
  }, [rules.data, q, prog, status]);

  if (rules.error) return <ErrorBox error={rules.error} onRetry={rules.reload} />;
  if (!rules.data || !analysis) return <PageLoading />;
  if (rules.data.length === 0) return <EmptyState title="No business rules found" body="Rules are paragraphs or annotated blocks containing decisions or computations." />;
  const current = rules.data.find((r) => r.id === sel) ?? list[0];
  const counts = rules.data.reduce<Record<string, number>>((m, r) => ((m[r.verification.status] = (m[r.verification.status] ?? 0) + 1), m), {});

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex min-w-64 flex-1 items-center gap-2 rounded-lg border border-ink-600 bg-ink-900 px-3 py-2">
          <Search className="h-4 w-4 text-fog-500" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search rules, fields, descriptions" className="w-full bg-transparent text-sm text-fog-100 outline-none placeholder:text-fog-500" />
        </div>
        <select value={prog} onChange={(e) => setProg(e.target.value)} className="rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-fog-200">
          <option value="">All programs</option>
          {analysis.programs
            .filter((p) => p.rules > 0)
            .map((p) => (
              <option key={p.program_id} value={p.program_id}>
                {p.program_id} ({p.rules})
              </option>
            ))}
        </select>
        <div className="flex flex-wrap gap-1.5">
          <Chip active={!status} onClick={() => setStatus("")}>
            all {rules.data.length}
          </Chip>
          {Object.entries(counts).map(([k, v]) => (
            <Chip key={k} active={status === k} onClick={() => setStatus(status === k ? "" : k)}>
              <span style={{ color: STATUS_META[k]?.dot }}>●</span> {k.toLowerCase().replace("_", " ")} {v}
            </Chip>
          ))}
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card className="h-fit max-h-[78vh] overflow-y-auto xl:sticky xl:top-6">
          {list.length === 0 && <div className="p-5 text-sm text-fog-500">No rules match the filters.</div>}
          <div className="divide-y divide-ink-700/70">
            {list.map((r) => (
              <button key={r.id} onClick={() => setSel(r.id)} className={cn("block w-full px-4 py-3 text-left transition", current?.id === r.id ? "bg-ink-700/70" : "hover:bg-ink-800/60")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-fog-50">{r.name}</span>
                  <StatusBadge status={r.verification.status} compact />
                </div>
                <div className="mt-1 line-clamp-2 text-xs text-fog-400">{r.description}</div>
                <div className="mt-1.5 font-mono text-[10.5px] text-fog-500">
                  {r.program} · {r.file}:{r.line_start}-{r.line_end}
                </div>
              </button>
            ))}
          </div>
        </Card>
        {current && <RuleDetail key={current.id} projectId={id} rule={current} />}
      </div>
    </div>
  );
}

function RuleDetail({ projectId, rule }: { projectId: string; rule: Rule }) {
  const file = useApi(() => api.file(projectId, rule.file), [projectId, rule.file]);
  const [exp, setExp] = useState<Explanation | null>(null);
  const [expBusy, setExpBusy] = useState(false);
  const [expErr, setExpErr] = useState<unknown>();
  const v = rule.verification;
  const from = Math.max(1, rule.line_start - 2);
  const snippet = file.data ? file.data.text.split("\n").slice(from - 1, rule.line_end + 1).join("\n") : "";
  async function explain() {
    setExpBusy(true);
    setExpErr(undefined);
    try {
      setExp(await api.explain(projectId, rule.id));
    } catch (e) {
      setExpErr(e);
    } finally {
      setExpBusy(false);
    }
  }
  return (
    <div className="min-w-0 space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-ink-700 px-5 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold text-fog-50">{rule.name}</h2>
              <StatusBadge status={v.status} />
            </div>
            <Link href={sourceHref(projectId, rule.file, rule.line_start, rule.line_end)} className="mt-1 inline-flex items-center gap-1 font-mono text-xs text-phoenix-300 hover:underline">
              {rule.file}:{rule.line_start}-{rule.line_end} · paragraph {rule.paragraph} <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
          <Button onClick={explain} loading={expBusy}>
            <Bot className="h-4 w-4" /> Explain
          </Button>
        </div>
        <div className="space-y-4 px-5 py-4">
          <div>
            <p className="text-sm leading-relaxed text-fog-200">{rule.description}</p>
            <div className="mt-1 text-[11px] text-fog-500">{rule.description_source === "source-comment" ? "Description taken from the annotated source comment" : "Description generated deterministically from the IR"}</div>
          </div>
          {expErr ? <ErrorBox error={expErr} /> : null}
          {exp && (
            <div className={cn("rounded-lg border px-4 py-3 text-sm", exp.advisory ? "border-violet-500/30 bg-violet-500/5" : "border-ink-600 bg-ink-900")}>
              <div className="mb-1 flex items-center gap-2 text-[11px] uppercase tracking-wider text-fog-500">
                <Bot className="h-3.5 w-3.5" /> {exp.advisory ? `AI explanation (advisory) · ${exp.provider}${exp.model ? ` / ${exp.model}` : ""}` : "Deterministic explanation"} · evidence {exp.evidence.file}:{exp.evidence.line_start}-{exp.evidence.line_end}
              </div>
              <p className="leading-relaxed text-fog-200">{exp.text}</p>
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            <FieldList title="Inputs" items={rule.inputs} tone="blue" />
            <FieldList title="Outputs" items={rule.outputs} tone="phoenix" />
          </div>
          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div className="rounded-lg border border-ink-600 bg-ink-900 p-2.5">
              <div className="text-fog-500">statements</div>
              <div className="text-lg font-semibold text-fog-50">{v.statements}</div>
            </div>
            <div className="rounded-lg border border-ink-600 bg-ink-900 p-2.5">
              <div className="text-fog-500">executed by tests</div>
              <div className="text-lg font-semibold text-fog-50">{v.executed}</div>
            </div>
            <div className="rounded-lg border border-ink-600 bg-ink-900 p-2.5">
              <div className="text-fog-500">coverage</div>
              <div className="text-lg font-semibold text-fog-50">{v.coverage_pct}%</div>
            </div>
          </div>
        </div>
      </Card>

      {(rule.conditions.length > 0 || rule.calculations.length > 0) && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title="Conditions" icon={<Split className="h-4 w-4" />} subtitle={`${rule.conditions.length} decision${rule.conditions.length === 1 ? "" : "s"}`} />
            <div className="space-y-1.5 p-4">
              {rule.conditions.length === 0 && <div className="text-xs text-fog-500">none</div>}
              {rule.conditions.map((c, i) => (
                <Link key={i} href={sourceHref(projectId, rule.file, c.line, c.end_line)} className="flex gap-3 rounded-md px-2 py-1.5 font-mono text-xs hover:bg-ink-800">
                  <span className="shrink-0 text-fog-500">{c.line}</span>
                  <span className="text-fog-100">IF {c.text}</span>
                </Link>
              ))}
            </div>
          </Card>
          <Card>
            <CardHeader title="Calculations" icon={<Calculator className="h-4 w-4" />} subtitle="Decimal arithmetic, explicit rounding" />
            <div className="space-y-1.5 p-4">
              {rule.calculations.length === 0 && <div className="text-xs text-fog-500">none</div>}
              {rule.calculations.map((c, i) => (
                <Link key={i} href={sourceHref(projectId, rule.file, c.line, c.end_line)} className="flex gap-3 rounded-md px-2 py-1.5 font-mono text-xs hover:bg-ink-800">
                  <span className="shrink-0 text-fog-500">{c.line}</span>
                  <span className="text-phoenix-200">{c.text}</span>
                </Link>
              ))}
            </div>
          </Card>
        </div>
      )}

      {rule.decision_tables.map((t, i) => (
        <Card key={i}>
          <CardHeader title={`Decision table — EVALUATE ${t.subject}`} subtitle={`line ${t.line}`} icon={<Table2 className="h-4 w-4" />} />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-ink-700 text-left text-[11px] uppercase tracking-wider text-fog-500">
                  <th className="px-5 py-2 font-medium">WHEN</th>
                  <th className="px-5 py-2 font-medium">Actions</th>
                  <th className="px-5 py-2 text-right font-medium">Line</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-700/60">
                {t.rows.map((r, j) => (
                  <tr key={j}>
                    <td className="px-5 py-2 font-mono text-sky-200">{r.when}</td>
                    <td className="px-5 py-2 font-mono text-fog-300">{r.actions.join("; ") || "—"}</td>
                    <td className="px-5 py-2 text-right font-mono text-fog-500">{r.line}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}

      <Card>
        <CardHeader title="Source evidence" subtitle={`${rule.file} lines ${rule.line_start}–${rule.line_end}`} icon={<ListChecks className="h-4 w-4" />} />
        <div className="p-3">
          {file.error ? <ErrorBox error={file.error} /> : file.data ? <CodeViewer text={snippet} language="cobol" startLine={from} highlight={[rule.line_start, rule.line_end]} maxHeight="420px" /> : <Spinner />}
        </div>
      </Card>
      {rule.related_paragraphs.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-fog-500">
          <GitBranch className="h-3.5 w-3.5" /> related paragraphs:
          {rule.related_paragraphs.map((p) => (
            <Badge key={p}>{p}</Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function FieldList({ title, items, tone }: { title: string; items: string[]; tone: "blue" | "phoenix" }) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] uppercase tracking-wider text-fog-500">
        {title} ({items.length})
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.length === 0 && <span className="text-xs text-fog-500">none</span>}
        {items.map((f) => (
          <Badge key={f} tone={tone} className="font-mono">
            {f}
          </Badge>
        ))}
      </div>
    </div>
  );
}
