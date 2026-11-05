"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Ban, Bug, Code2, Download, FileCode2, FlaskConical, PlayCircle, Sparkles, Workflow } from "lucide-react";
import { CodeViewer } from "@/components/code-viewer";
import { useProject } from "@/components/project-context";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBox, LinkButton, PageLoading, PageTitle, Spinner, cn } from "@/components/ui";
import { api, type Generation, type InterfaceNode, type Mutation } from "@/lib/api";
import { fmtDate, useApi } from "@/lib/use-api";

export default function GeneratePage() {
  const { id, analysis } = useProject();
  const router = useRouter();
  const gens = useApi(() => api.generations(id), [id]);
  const [entry, setEntry] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [viewGen, setViewGen] = useState<string | null>(null);

  const programs = useMemo(() => (analysis?.programs ?? []).slice().sort((a, b) => a.unsupported - b.unsupported || (a.kind === "subprogram" ? -1 : 1)), [analysis]);
  useEffect(() => {
    if (!entry && programs.length) setEntry((programs.find((p) => p.unsupported === 0 && p.kind === "subprogram") ?? programs[0]).program_id);
  }, [programs, entry]);

  async function generate(mutation_id?: string) {
    setBusy(true);
    setError(undefined);
    try {
      const g = await api.generate(id, { entry, mutation_id });
      gens.reload();
      setViewGen(g.id);
      if (mutation_id) router.push(`/projects/${id}/verify?gen=${g.id}`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (!analysis) return <PageLoading />;
  const sel = programs.find((p) => p.program_id === entry);
  const shown = (gens.data ?? []).find((g) => g.id === viewGen) ?? (gens.data ?? []).find((g) => !g.mutation_id);

  return (
    <div className="space-y-6">
      <PageTitle eyebrow="Act III · The resurrection" title="Generate a Python service" subtitle="Deterministic, template-based translation of the selected program and everything it CALLs. No LLM writes code here." />
      {error ? <ErrorBox error={error} /> : null}
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="1 · Choose a business capability" subtitle="Programs with a LINKAGE SECTION become typed JSON endpoints; main programs become stdin/stdout batch endpoints" icon={<Workflow className="h-4 w-4" />} />
          <div className="grid gap-2 p-4 sm:grid-cols-2">
            {programs.map((p) => (
              <button
                key={p.program_id}
                onClick={() => setEntry(p.program_id)}
                className={cn("rounded-lg border p-3 text-left transition", entry === p.program_id ? "border-phoenix-500/60 bg-phoenix-500/5 ring-1 ring-phoenix-500/30" : "border-ink-600 bg-ink-900 hover:border-ink-500")}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-sm text-fog-50">{p.program_id}</span>
                  {p.unsupported > 0 ? (
                    <Badge tone="violet">
                      <Ban className="h-3 w-3" /> {p.unsupported} unsupported
                    </Badge>
                  ) : (
                    <Badge tone="green">fully translatable</Badge>
                  )}
                </div>
                <div className="mt-1 text-[11px] text-fog-500">
                  {p.kind}
                  {p.using.length ? ` · USING ${p.using.join(", ")}` : ""} · {p.metrics.statements} statements · {p.rules} rules
                </div>
                {p.calls.length > 0 && <div className="mt-1 font-mono text-[10.5px] text-phoenix-300/80">CALL {Array.from(new Set(p.calls.map((c) => c.target))).join(", ")}</div>}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-700 px-4 py-3">
            <div className="text-xs text-fog-500">
              {sel?.unsupported ? "Unsupported statements will be generated as explicit UnsupportedConstruct errors." : "Every statement in the call tree is inside the supported subset."}
            </div>
            <Button variant="primary" onClick={() => generate()} loading={busy} disabled={!entry}>
              <Sparkles className="h-4 w-4" /> Generate {entry}
            </Button>
          </div>
        </Card>

        <FaultInjector projectId={id} entry={entry} onInject={(m) => generate(m)} busy={busy} />
      </div>

      <Card>
        <CardHeader title="2 · Generated services" subtitle="Each generation is an executable Python/FastAPI project with tests and a traceability map" icon={<FileCode2 className="h-4 w-4" />} />
        {gens.loading && !gens.data ? (
          <div className="p-5">
            <Spinner />
          </div>
        ) : !gens.data?.length ? (
          <div className="p-5">
            <EmptyState title="Nothing generated yet" body="Pick a program above and generate its Python service." icon={<Sparkles className="h-8 w-8" />} />
          </div>
        ) : (
          <div className="divide-y divide-ink-700">
            {gens.data.map((g) => (
              <GenerationRow key={g.id} g={g} projectId={id} active={shown?.id === g.id} onSelect={() => setViewGen(g.id)} />
            ))}
          </div>
        )}
      </Card>

      {shown && <ApiPreview gid={shown.id} />}
    </div>
  );
}

function GenerationRow({ g, projectId, active, onSelect }: { g: Generation; projectId: string; active: boolean; onSelect: () => void }) {
  const s = g.summary;
  return (
    <div className={cn("flex flex-wrap items-center gap-4 px-5 py-3.5", active && "bg-ink-800/50")}>
      <button onClick={onSelect} className="min-w-0 flex-1 text-left">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-sm text-fog-50">{g.name}</span>
          <Badge tone={s.mode === "linkage" ? "violet" : "neutral"}>{s.mode === "linkage" ? "typed JSON API" : "batch API"}</Badge>
          {g.mutation_id && (
            <Badge tone="red">
              <Bug className="h-3 w-3" /> injected fault
            </Badge>
          )}
        </div>
        <div className="mt-1 text-xs text-fog-500">
          {s.call_tree.join(" → ")} · {s.statements} statements traced · {s.lines_of_code} lines of Python · {s.unsupported.length} unsupported · {fmtDate(g.created_at)}
        </div>
        {g.mutation_detail && <div className="mt-1 font-mono text-[11px] text-rose-300/80">{g.mutation_id}: {g.mutation_detail}</div>}
      </button>
      <div className="flex flex-wrap gap-2">
        <LinkButton href={`/projects/${projectId}/generations/${g.id}`}>
          <Code2 className="h-4 w-4" /> Code
        </LinkButton>
        <a href={api.downloadUrl(g.id)} className="inline-flex items-center gap-2 rounded-lg border border-ink-500 bg-ink-800 px-3.5 py-2 text-sm text-fog-100 hover:bg-ink-700">
          <Download className="h-4 w-4" /> ZIP
        </a>
        <LinkButton href={`/projects/${projectId}/verify?gen=${g.id}`} variant="primary">
          <PlayCircle className="h-4 w-4" /> Verify
        </LinkButton>
      </div>
    </div>
  );
}

function FaultInjector({ projectId, entry, onInject, busy }: { projectId: string; entry: string; onInject: (id: string) => void; busy: boolean }) {
  const muts = useApi(() => api.mutations(projectId, entry), [projectId, entry], !!entry);
  const [pick, setPick] = useState<string>("");
  const list = muts.data ?? [];
  const kinds: Record<Mutation["kind"], string> = { rounding: "Drop ROUNDED", relop: "Off-by-one comparison", arith: "Swap + / −", literal: "Tweak a constant" };
  useEffect(() => setPick(""), [entry]);
  return (
    <Card>
      <CardHeader title="Inject a deliberate fault" subtitle="Prove the verifier catches wrong behaviour: generate a copy with exactly one semantic change, then verify it" icon={<FlaskConical className="h-4 w-4" />} />
      <div className="space-y-3 p-4">
        {muts.loading ? (
          <Spinner />
        ) : muts.error ? (
          <ErrorBox error={muts.error} />
        ) : list.length === 0 ? (
          <div className="text-sm text-fog-500">No mutation sites in {entry}.</div>
        ) : (
          <div className="max-h-72 space-y-1 overflow-y-auto pr-1">
            {list.map((m) => (
              <label key={m.id} className={cn("flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 text-xs transition", pick === m.id ? "border-rose-400/50 bg-rose-500/5" : "border-ink-600 bg-ink-900 hover:border-ink-500")}>
                <input type="radio" name="mut" className="mt-0.5 accent-rose-400" checked={pick === m.id} onChange={() => setPick(m.id)} />
                <span className="flex-1">
                  <span className="text-fog-100">{kinds[m.kind]}</span> <span className="text-fog-400">— {m.detail}</span>
                  <span className="mt-0.5 block font-mono text-[10.5px] text-fog-500">
                    {m.file}:{m.line}
                  </span>
                </span>
              </label>
            ))}
          </div>
        )}
        <div className="flex justify-end">
          <Button variant="danger" disabled={!pick} loading={busy} onClick={() => onInject(pick)}>
            <Bug className="h-4 w-4" /> Generate faulty build & verify
          </Button>
        </div>
      </div>
    </Card>
  );
}

function ApiPreview({ gid }: { gid: string }) {
  const g = useApi(() => api.generation(gid), [gid]);
  if (g.error) return <ErrorBox error={g.error} />;
  if (!g.data) return <Spinner label="Loading API schema" />;
  const d = g.data;
  return (
    <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
      <Card>
        <CardHeader title="API contract" subtitle={<span className="font-mono">POST {d.summary.endpoint}</span>} icon={<Sparkles className="h-4 w-4" />} />
        <div className="max-h-[520px] space-y-4 overflow-y-auto p-4 text-xs">
          {d.interface.mode === "main" ? (
            <p className="text-fog-400">Batch program: the request carries the lines read by ACCEPT and the response returns everything DISPLAYed.</p>
          ) : (
            d.interface.params.map((p) => (
              <div key={p.name}>
                <div className="font-mono text-fog-100">
                  {p.py} <span className="text-fog-500">— USING {p.name} ({p.size} bytes)</span>
                </div>
                <div className="mt-1.5 grid grid-cols-2 gap-3">
                  <Tree title="request (inputs read)" nodes={p.inputs} tone="text-sky-200" />
                  <Tree title="response (outputs written)" nodes={p.outputs} tone="text-phoenix-200" />
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
      <Card>
        <CardHeader title="app/schemas.py" subtitle="Pydantic v2 models derived from the COBOL PICTURE clauses" icon={<Code2 className="h-4 w-4" />} actions={<LinkButton href={`/projects/${d.project_id}/generations/${gid}`}>Open code viewer</LinkButton>} />
        <div className="p-3">
          <CodeViewer text={d.schemas} language="python" maxHeight="520px" />
        </div>
      </Card>
    </div>
  );
}

function Tree({ title, nodes, tone }: { title: string; nodes: InterfaceNode[]; tone: string }) {
  return (
    <div>
      <div className="mb-1 text-[10px] uppercase tracking-wider text-fog-500">{title}</div>
      {nodes.length === 0 && <div className="text-fog-500">—</div>}
      {nodes.map((n) => (
        <div key={n.py} className="font-mono leading-5">
          <span className={tone}>{n.py}</span>
          {n.occurs ? <span className="text-fog-500"> [{n.occurs}]</span> : <span className="text-fog-500"> {n.picture}</span>}
          {n.children && (
            <div className="ml-3 border-l border-ink-600 pl-2">
              {n.children.map((c) => (
                <div key={c.py}>
                  <span className={tone}>{c.py}</span> <span className="text-fog-500">{c.picture}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

