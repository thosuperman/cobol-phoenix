"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, FileArchive, FileJson, FileText, Network, Route, ScrollText, ShieldCheck } from "lucide-react";
import { useProject } from "@/components/project-context";
import { Card, CardHeader, ErrorBox, PageTitle, Segmented, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";

const EXPORTS = [
  { kind: "migration-report.md", title: "Migration report", body: "Inventory, complexity, unsupported constructs, generated services, verification status and next steps.", icon: ScrollText },
  { kind: "verification-report.md", title: "Verification report", body: "Latest differential run: environment, totals, field-level differences, mutation analysis, every case.", icon: ShieldCheck },
  { kind: "verification-report.json", title: "Verification data (JSON)", body: "Machine-readable report including raw COBOL and Python outputs.", icon: FileJson },
  { kind: "rules.md", title: "Business rule documentation", body: "Every extracted rule with source line ranges, inputs, outputs, conditions, calculations and status.", icon: FileText },
  { kind: "rules.json", title: "Business rules (JSON)", body: "Structured rules for import into other tools.", icon: FileJson },
  { kind: "graph.json", title: "Dependency graph", body: "Nodes and edges (COPY, CALL, PERFORM, data usage) with source references.", icon: Network },
  { kind: "traceability.json", title: "Source → Python traceability", body: "Mapping from every generated Python statement to its COBOL file and line range.", icon: Route },
];

export default function ExportPage() {
  const { id } = useProject();
  const gens = useApi(() => api.generations(id), [id]);
  const [preview, setPreview] = useState<"migration-report.md" | "verification-report.md" | "rules.md">("migration-report.md");
  const md = useApi(async () => {
    const r = await fetch(api.exportUrl(id, preview));
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.text();
  }, [id, preview]);
  return (
    <div className="space-y-6">
      <PageTitle eyebrow="Export" title="Reports and artifacts" subtitle="Everything an enterprise team needs to review, audit and continue the modernization." />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {EXPORTS.map((e) => (
          <a key={e.kind} href={api.exportUrl(id, e.kind)} className="group rounded-xl border border-ink-600/70 bg-ink-850/70 p-4 transition hover:border-phoenix-500/40">
            <div className="flex items-center justify-between">
              <e.icon className="h-5 w-5 text-phoenix-400" />
              <Download className="h-4 w-4 text-fog-500 group-hover:text-phoenix-300" />
            </div>
            <div className="mt-3 font-medium text-fog-50">{e.title}</div>
            <div className="mt-1 text-xs leading-relaxed text-fog-400">{e.body}</div>
            <div className="mt-2 font-mono text-[10.5px] text-fog-500">{e.kind}</div>
          </a>
        ))}
        <div className="rounded-xl border border-ink-600/70 bg-ink-850/70 p-4">
          <FileArchive className="h-5 w-5 text-phoenix-400" />
          <div className="mt-3 font-medium text-fog-50">Generated Python projects</div>
          <div className="mt-1 text-xs text-fog-400">Executable FastAPI service with tests, README and traceability.</div>
          <div className="mt-3 space-y-1">
            {gens.data?.length === 0 && <div className="text-xs text-fog-500">none generated yet</div>}
            {gens.data
              ?.filter((g) => !g.mutation_id)
              .map((g) => (
                <a key={g.id} href={api.downloadUrl(g.id)} className="flex items-center gap-2 font-mono text-xs text-phoenix-300 hover:underline">
                  <Download className="h-3 w-3" /> {g.name}.zip
                </a>
              ))}
          </div>
        </div>
      </div>
      <Card>
        <CardHeader
          title="Preview"
          icon={<ScrollText className="h-4 w-4" />}
          actions={
            <Segmented
              value={preview}
              onChange={setPreview}
              options={[
                { value: "migration-report.md", label: "Migration" },
                { value: "verification-report.md", label: "Verification" },
                { value: "rules.md", label: "Rules" },
              ]}
            />
          }
        />
        <div className="md max-h-[70vh] overflow-y-auto px-6 py-5 text-sm">
          {md.error ? <ErrorBox error={md.error} /> : md.loading ? <Spinner /> : md.data === null ? <div className="text-fog-500">Not available yet — run a verification first.</div> : <ReactMarkdown remarkPlugins={[remarkGfm]}>{md.data ?? ""}</ReactMarkdown>}
        </div>
      </Card>
    </div>
  );
}
