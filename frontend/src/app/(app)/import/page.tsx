"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type DragEvent } from "react";
import { FileArchive, FolderOpen, FolderGit2 as Github, ShieldCheck, Sparkles, UploadCloud, X } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, CardHeader, ErrorBox, PageTitle, Segmented, cn } from "@/components/ui";

type Tab = "sample" | "upload" | "github" | "local";

const PRESETS = [
  {
    repo: "mudasin1/COBOL_Sample_March_2026",
    label: "Term life insurance (primary corpus)",
    note: "NB-UW-001 eligibility & premium, servicing, claims. No license file: analyse locally, do not redistribute.",
    subdir: "",
  },
  { repo: "achalc/cobol-bank-demo", label: "Banking demo (validation corpus)", note: "Interactive banking with sequential files — exercises unsupported-construct reporting. No license file.", subdir: "" },
  { repo: "albertdobmeyer/cobol-legacy-ledger", label: "Legacy ledger (advanced corpus, MIT)", note: "Free-format COBOL with file I/O, ALTER, REPORT SECTION, SORT.", subdir: "COBOL-BANKING" },
];

const ACCEPT = ".cob,.cbl,.cpy,.cobol,.copy,.cbk,.zip,.json,.md,.txt";

export default function ImportPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("sample");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [files, setFiles] = useState<File[]>([]);
  const [name, setName] = useState("");
  const [fmt, setFmt] = useState("auto");
  const [repo, setRepo] = useState(PRESETS[0].repo);
  const [ref, setRef] = useState("HEAD");
  const [subdir, setSubdir] = useState("");
  const [local, setLocal] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function run(fn: () => Promise<{ id: string }>) {
    setBusy(true);
    setError(undefined);
    try {
      const p = await fn();
      router.push(`/projects/${p.id}`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    setFiles((f) => [...f, ...Array.from(e.dataTransfer.files)]);
  }

  return (
    <div className="animate-fade-up max-w-4xl">
      <PageTitle eyebrow="Act I · The dead system" title="Import a COBOL project" subtitle="Bring COBOL programs and copybooks into COBOL Phoenix. Imported code is stored as data and is never executed during import or analysis." />
      <Segmented<Tab>
        value={tab}
        onChange={setTab}
        options={[
          { value: "sample", label: "Sample project" },
          { value: "upload", label: "Files / ZIP" },
          { value: "github", label: "GitHub repository" },
          { value: "local", label: "Local directory" },
        ]}
      />
      <div className="mt-5 space-y-5">
        {error ? <ErrorBox error={error} /> : null}
        {tab === "sample" && (
          <Card>
            <CardHeader title="Phoenix Mutual — auto premium rating" subtitle="Original sample written for COBOL Phoenix · Apache-2.0" icon={<Sparkles className="h-4 w-4" />} />
            <div className="space-y-4 p-5 text-sm text-fog-300">
              <p>
                A nightly batch (<code className="font-mono text-phoenix-300">PREMCALC</code>) calls a rating engine (<code className="font-mono text-phoenix-300">RATEENG</code>) that validates
                policies, looks up state base rates in a REDEFINES/OCCURS table, applies age, vehicle, coverage and deductible factors, risk points, discounts and a minimum premium.
                A third program (<code className="font-mono text-phoenix-300">AUDITLOG</code>) uses file I/O on purpose to show unsupported-construct reporting.
              </p>
              <div className="flex flex-wrap gap-2">
                {["3 programs", "3 copybooks", "13 fixture policies", "expected output from GnuCOBOL 3.2"].map((x) => (
                  <Badge key={x}>{x}</Badge>
                ))}
              </div>
              <Button variant="primary" loading={busy} onClick={() => run(api.importSample)}>
                Import sample project
              </Button>
            </div>
          </Card>
        )}
        {tab === "upload" && (
          <Card>
            <CardHeader title="Upload source files or a ZIP archive" subtitle=".cob .cbl .cpy … or a single .zip — max 25 MB" icon={<UploadCloud className="h-4 w-4" />} />
            <div className="space-y-4 p-5">
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDrag(true);
                }}
                onDragLeave={() => setDrag(false)}
                onDrop={onDrop}
                onClick={() => input.current?.click()}
                className={cn("grid-bg flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-6 py-10 text-center transition", drag ? "border-phoenix-500 bg-phoenix-500/5" : "border-ink-500 hover:border-ink-500")}
              >
                <FileArchive className="h-8 w-8 text-fog-500" />
                <div className="mt-2 text-sm text-fog-200">Drop COBOL files or a ZIP here, or click to browse</div>
                <div className="mt-1 text-xs text-fog-500">Archives are checked for path traversal, symlinks, size and compression ratio before extraction</div>
                <input ref={input} type="file" multiple accept={ACCEPT} className="hidden" onChange={(e) => setFiles((f) => [...f, ...Array.from(e.target.files ?? [])])} />
              </div>
              {files.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {files.map((f, i) => (
                    <span key={i} className="inline-flex items-center gap-1.5 rounded-md border border-ink-600 bg-ink-800 px-2 py-1 font-mono text-xs text-fog-200">
                      {f.name}
                      <button onClick={() => setFiles(files.filter((_, j) => j !== i))} aria-label={`remove ${f.name}`}>
                        <X className="h-3 w-3 text-fog-500 hover:text-rose-300" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
              <Fields name={name} setName={setName} fmt={fmt} setFmt={setFmt} />
              <Button variant="primary" loading={busy} disabled={files.length === 0} onClick={() => run(() => api.upload(files, name || files[0]?.name || "Uploaded project", fmt))}>
                Import {files.length > 0 ? `${files.length} file${files.length > 1 ? "s" : ""}` : ""}
              </Button>
            </div>
          </Card>
        )}
        {tab === "github" && (
          <Card>
            <CardHeader title="Import a public GitHub repository" subtitle="Downloads the repository archive from codeload.github.com and imports COBOL sources only" icon={<Github className="h-4 w-4" />} />
            <div className="space-y-4 p-5">
              <div className="grid gap-2">
                {PRESETS.map((p) => (
                  <button
                    key={p.repo}
                    onClick={() => {
                      setRepo(p.repo);
                      setSubdir(p.subdir);
                      setName("");
                    }}
                    className={cn("rounded-lg border px-4 py-3 text-left transition", repo === p.repo ? "border-phoenix-500/50 bg-phoenix-500/5" : "border-ink-600 bg-ink-900 hover:border-ink-500")}
                  >
                    <div className="flex items-center gap-2 text-sm text-fog-100">
                      <Github className="h-3.5 w-3.5" /> <span className="font-mono">{p.repo}</span>
                      <Badge tone="phoenix">{p.label}</Badge>
                    </div>
                    <div className="mt-1 text-xs text-fog-500">{p.note}</div>
                  </button>
                ))}
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <label className="text-xs text-fog-400 sm:col-span-2">
                  Repository
                  <input value={repo} onChange={(e) => setRepo(e.target.value)} className="mt-1 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 font-mono text-sm text-fog-100 outline-none focus:border-phoenix-500" />
                </label>
                <label className="text-xs text-fog-400">
                  Ref (branch, tag or commit)
                  <input value={ref} onChange={(e) => setRef(e.target.value)} className="mt-1 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 font-mono text-sm text-fog-100 outline-none focus:border-phoenix-500" />
                </label>
                <label className="text-xs text-fog-400 sm:col-span-3">
                  Sub-directory (optional)
                  <input value={subdir} onChange={(e) => setSubdir(e.target.value)} placeholder="e.g. COBOL-BANKING" className="mt-1 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 font-mono text-sm text-fog-100 outline-none focus:border-phoenix-500" />
                </label>
              </div>
              <Fields name={name} setName={setName} fmt={fmt} setFmt={setFmt} />
              <p className="flex items-start gap-2 text-xs text-fog-500">
                <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                Respect the repository license. Repositories without a license file are all-rights-reserved: analyse them, but do not redistribute their code or generated derivatives.
              </p>
              <Button variant="primary" loading={busy} disabled={!repo} onClick={() => run(() => api.importGithub({ repo, ref, subdir: subdir || undefined, name: name || undefined, source_format: fmt }))}>
                Download and import
              </Button>
            </div>
          </Card>
        )}
        {tab === "local" && (
          <Card>
            <CardHeader title="Import a directory on the server" subtitle="Disabled unless PHOENIX_ALLOW_LOCAL_IMPORT=true; paths are confined to PHOENIX_LOCAL_IMPORT_ROOT" icon={<FolderOpen className="h-4 w-4" />} />
            <div className="space-y-4 p-5">
              <label className="block text-xs text-fog-400">
                Path (relative to the import root)
                <input value={local} onChange={(e) => setLocal(e.target.value)} placeholder="legacy/claims" className="mt-1 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 font-mono text-sm text-fog-100 outline-none focus:border-phoenix-500" />
              </label>
              <Fields name={name} setName={setName} fmt={fmt} setFmt={setFmt} />
              <Button variant="primary" loading={busy} disabled={!local} onClick={() => run(() => api.importLocal({ path: local, name: name || undefined, source_format: fmt }))}>
                Import directory
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function Fields({ name, setName, fmt, setFmt }: { name: string; setName: (v: string) => void; fmt: string; setFmt: (v: string) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <label className="text-xs text-fog-400 sm:col-span-2">
        Project name (optional)
        <input value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-fog-100 outline-none focus:border-phoenix-500" />
      </label>
      <label className="text-xs text-fog-400">
        Source format
        <select value={fmt} onChange={(e) => setFmt(e.target.value)} className="mt-1 w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-fog-100 outline-none focus:border-phoenix-500">
          <option value="auto">Auto-detect</option>
          <option value="fixed">Fixed (cols 8–72)</option>
          <option value="free">Free format</option>
        </select>
      </label>
    </div>
  );
}
