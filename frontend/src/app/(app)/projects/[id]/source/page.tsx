"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { BookOpen, FileCode2, FileText, Folder, ListTree, Search } from "lucide-react";
import { CodeViewer } from "@/components/code-viewer";
import { sourceHref, useProject } from "@/components/project-context";
import { Badge, Card, CardHeader, EmptyState, ErrorBox, PageLoading, Spinner, cn } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";

function SourceExplorer() {
  const { id, analysis } = useProject();
  const params = useSearchParams();
  const router = useRouter();
  const [filter, setFilter] = useState("");
  const files = analysis?.files ?? [];
  const selected = params.get("file") ?? files.find((f) => f.kind === "program")?.path ?? files[0]?.path;
  const line = Number(params.get("line") ?? 0) || undefined;
  const end = Number(params.get("end") ?? 0) || line;
  const file = useApi(() => api.file(id, selected!), [id, selected], !!selected);
  const meta = files.find((f) => f.path === selected);
  const programs = analysis?.programs.filter((p) => p.file === selected) ?? [];
  const groups = useMemo(() => {
    const g: Record<string, typeof files> = {};
    for (const f of files.filter((f) => f.path.toLowerCase().includes(filter.toLowerCase()))) {
      const dir = f.path.includes("/") ? f.path.slice(0, f.path.lastIndexOf("/")) : ".";
      (g[dir] ??= []).push(f);
    }
    return Object.entries(g).sort(([a], [b]) => a.localeCompare(b));
  }, [files, filter]);
  if (!analysis) return <PageLoading />;
  if (files.length === 0) return <EmptyState title="No files" />;
  const lang = selected && /\.(cob|cbl|cpy|cobol|copy|cbk)$/i.test(selected) ? "cobol" : selected?.endsWith(".json") ? "json" : "text";
  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <Card className="h-fit lg:sticky lg:top-6">
        <div className="border-b border-ink-700 p-3">
          <div className="flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-900 px-2.5 py-1.5">
            <Search className="h-3.5 w-3.5 text-fog-500" />
            <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter files" className="w-full bg-transparent text-sm text-fog-100 outline-none placeholder:text-fog-500" />
          </div>
        </div>
        <div className="max-h-[70vh] overflow-y-auto p-2">
          {groups.map(([dir, fs]) => (
            <div key={dir} className="mb-2">
              <div className="flex items-center gap-1.5 px-2 py-1 text-[11px] uppercase tracking-wider text-fog-500">
                <Folder className="h-3 w-3" /> {dir}
              </div>
              {fs.map((f) => (
                <button
                  key={f.path}
                  onClick={() => router.push(sourceHref(id, f.path))}
                  className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] transition", f.path === selected ? "bg-ink-700 text-fog-50" : "text-fog-400 hover:bg-ink-800 hover:text-fog-100")}
                >
                  {f.kind === "program" ? <FileCode2 className="h-3.5 w-3.5 text-phoenix-400" /> : f.kind === "copybook" ? <BookOpen className="h-3.5 w-3.5 text-sky-400" /> : <FileText className="h-3.5 w-3.5" />}
                  <span className="truncate">{f.path.split("/").pop()}</span>
                  <span className="ml-auto text-[10px] text-fog-500">{f.lines}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      </Card>
      <div className="min-w-0 space-y-4">
        <Card>
          <CardHeader
            title={<span className="font-mono">{selected}</span>}
            subtitle={meta ? `${meta.kind} · ${meta.format} format · ${meta.lines} lines${line ? ` · showing lines ${line}${end && end !== line ? `–${end}` : ""}` : ""}` : undefined}
            icon={<FileCode2 className="h-4 w-4" />}
            actions={programs.map((p) => (
              <Badge key={p.program_id} tone="phoenix">
                {p.program_id}
              </Badge>
            ))}
          />
          <div className="p-3">
            {file.error ? <ErrorBox error={file.error} /> : file.loading || !file.data ? <Spinner label="Loading source" /> : <CodeViewer text={file.data.text} language={lang} highlight={line ? [line, end ?? line] : null} fixedFormat={meta?.format !== "free"} scrollKey={`${selected}:${line}`} />}
          </div>
        </Card>
        {programs.length > 0 && (
          <Card>
            <CardHeader title="Outline" subtitle="Paragraphs parsed from the PROCEDURE DIVISION" icon={<ListTree className="h-4 w-4" />} />
            <div className="flex flex-wrap gap-1.5 p-4">
              {programs.flatMap((p) =>
                p.paragraphs.map((pa) => (
                  <button
                    key={`${p.program_id}:${pa.name}`}
                    onClick={() => router.push(sourceHref(id, p.file, pa.line_start, pa.line_end))}
                    className={cn("rounded-md border px-2 py-1 font-mono text-[11px] transition", line && line >= pa.line_start && line <= pa.line_end ? "border-phoenix-500/60 bg-phoenix-500/10 text-phoenix-200" : "border-ink-600 bg-ink-800 text-fog-300 hover:text-fog-50")}
                  >
                    {pa.name} <span className="text-fog-500">{pa.line_start}</span>
                  </button>
                )),
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

export default function SourcePage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <SourceExplorer />
    </Suspense>
  );
}
