"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowLeftRight, Bug, Download, FileCode2, FileJson, FileText, PlayCircle } from "lucide-react";
import { CodeViewer } from "@/components/code-viewer";
import { sourceHref } from "@/components/project-context";
import { Badge, Card, CardHeader, ErrorBox, LinkButton, PageLoading, Spinner, cn } from "@/components/ui";
import { api, type TraceEntry } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function GeneratedCodePage() {
  const { id, gid } = useParams<{ id: string; gid: string }>();
  const gen = useApi(() => api.generation(gid), [gid]);
  const trace = useApi(() => api.traceability(gid), [gid]);
  const files = gen.data?.summary.files ?? [];
  const defaultFile = gen.data ? (gen.data.summary.modules[0]?.module ?? "app/main.py") : "";
  const [file, setFile] = useState<string>("");
  const current = file || defaultFile;
  const src = useApi(() => api.generationFile(gid, current), [gid, current], !!current);
  const [pyLine, setPyLine] = useState<number | null>(null);

  const entries = useMemo(() => (trace.data ?? []).filter((t) => t.python_file === current), [trace.data, current]);
  const marks = useMemo(() => new Set(entries.map((e) => e.python_start)), [entries]);
  const hit: TraceEntry | undefined = useMemo(() => {
    if (pyLine == null) return undefined;
    const cands = entries.filter((e) => pyLine >= e.python_start - 1 && pyLine <= e.python_end);
    return cands.sort((a, b) => a.python_end - a.python_start - (b.python_end - b.python_start))[0];
  }, [pyLine, entries]);
  const cobol = useApi(() => api.file(id, hit!.cobol_file), [id, hit?.cobol_file], !!hit);

  if (gen.error) return <ErrorBox error={gen.error} onRetry={gen.reload} />;
  if (!gen.data) return <PageLoading />;
  const g = gen.data;
  const icon = (f: string) => (f.endsWith(".py") ? <FileCode2 className="h-3.5 w-3.5 text-phoenix-400" /> : f.endsWith(".json") ? <FileJson className="h-3.5 w-3.5 text-sky-400" /> : <FileText className="h-3.5 w-3.5" />);
  const lang = current.endsWith(".py") ? "python" : current.endsWith(".json") ? "json" : "text";
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-phoenix-400">Generated code</div>
          <h2 className="mt-1 flex flex-wrap items-center gap-2 text-xl font-semibold text-fog-50">
            <span className="font-mono">{g.name}</span>
            {g.mutation_id && (
              <Badge tone="red">
                <Bug className="h-3 w-3" /> {g.mutation_detail}
              </Badge>
            )}
          </h2>
          <div className="mt-1 text-xs text-fog-500">
            {g.summary.call_tree.join(" → ")} · {g.summary.statements} COBOL statements mapped · endpoint <span className="font-mono">{g.summary.endpoint}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <a href={api.downloadUrl(gid)} className="inline-flex items-center gap-2 rounded-lg border border-ink-500 bg-ink-800 px-3.5 py-2 text-sm text-fog-100 hover:bg-ink-700">
            <Download className="h-4 w-4" /> Download ZIP
          </a>
          <LinkButton href={`/projects/${id}/verify?gen=${gid}`} variant="primary">
            <PlayCircle className="h-4 w-4" /> Verify against GnuCOBOL
          </LinkButton>
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-[240px_minmax(0,1fr)_minmax(0,0.85fr)]">
        <Card className="h-fit">
          <CardHeader title="Files" subtitle={`${files.length} files`} />
          <div className="max-h-[70vh] overflow-y-auto p-2">
            {files.map((f) => (
              <button
                key={f}
                onClick={() => {
                  setFile(f);
                  setPyLine(null);
                }}
                className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left font-mono text-[12px] transition", f === current ? "bg-ink-700 text-fog-50" : "text-fog-400 hover:bg-ink-800 hover:text-fog-100")}
              >
                {icon(f)}
                <span className="truncate">{f}</span>
              </button>
            ))}
          </div>
        </Card>
        <Card className="min-w-0">
          <CardHeader title={<span className="font-mono">{current}</span>} subtitle={entries.length ? `${entries.length} traced statements · click a line to see its COBOL origin` : "no COBOL trace entries in this file"} icon={<FileCode2 className="h-4 w-4" />} />
          <div className="p-3">{src.error ? <ErrorBox error={src.error} /> : !src.data ? <Spinner /> : <CodeViewer text={src.data.text} language={lang} marks={marks} highlight={hit ? [hit.python_start - 1, hit.python_end] : null} onLineClick={entries.length ? setPyLine : undefined} />}</div>
        </Card>
        <Card className="min-w-0">
          <CardHeader title="COBOL origin" subtitle={hit ? `${hit.cobol_file}:${hit.cobol_start}-${hit.cobol_end} · ${hit.construct} in ${hit.paragraph}` : "Select a traced Python line (●)"} icon={<ArrowLeftRight className="h-4 w-4" />} actions={hit && <Link href={sourceHref(id, hit.cobol_file, hit.cobol_start, hit.cobol_end)} className="text-xs text-phoenix-300 hover:underline">open in explorer</Link>} />
          <div className="p-3">
            {!hit ? (
              <div className="grid-bg rounded-lg border border-dashed border-ink-500 p-8 text-center text-sm text-fog-500">Every generated statement carries a traceability entry back to the COBOL file and line range it was translated from.</div>
            ) : cobol.error ? (
              <ErrorBox error={cobol.error} />
            ) : !cobol.data ? (
              <Spinner />
            ) : (
              <CodeViewer text={cobol.data.text} language="cobol" highlight={[hit.cobol_start, hit.cobol_end]} scrollKey={`${hit.cobol_file}:${hit.cobol_start}`} />
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
