"use client";

import { useEffect, useState } from "react";
import { ClipboardList, Save } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { Button, ErrorBox } from "./ui";

const EXAMPLE = `{
  "PROGRAM-ID": [
    { "id": "happy-path", "description": "…", "inputs": { "LINKAGE-RECORD": { "FIELD-NAME": "value", "TABLE-FIELD(1)": "value" } } },
    { "id": "batch-run", "description": "for main programs", "stdin": "line 1\\nline 2\\n" }
  ]
}`;

export function FixturesEditor({ projectId }: { projectId: string }) {
  const fx = useApi(() => api.fixtures(projectId), [projectId]);
  const [text, setText] = useState("");
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (fx.data) setText(JSON.stringify(fx.data, null, 2));
  }, [fx.data]);
  const count = fx.data ? Object.values(fx.data).reduce((n, l) => n + l.length, 0) : 0;
  async function save() {
    setBusy(true);
    setErr(undefined);
    setSaved(false);
    try {
      await api.saveFixtures(projectId, JSON.parse(text));
      setSaved(true);
      fx.reload();
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="rounded-xl border border-ink-600/70 bg-ink-850/80">
      <summary className="flex cursor-pointer items-center gap-2 px-5 py-3 text-sm text-fog-200">
        <ClipboardList className="h-4 w-4 text-phoenix-400" /> Test fixtures <span className="text-xs text-fog-500">({count} fixture cases · used as baselines for boundary and random cases)</span>
      </summary>
      <div className="space-y-3 border-t border-ink-700 p-4">
        <p className="text-xs text-fog-400">
          Fixtures are keyed by PROGRAM-ID. Linkage programs take field values per USING record (keys are COBOL names; subscripts like <code className="font-mono">NAME(2)</code>; prefix <code className="font-mono">raw:</code> for raw bytes). Main programs take{" "}
          <code className="font-mono">stdin</code>. Projects can ship them as <code className="font-mono">phoenix-fixtures.json</code>.
        </p>
        <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} placeholder={EXAMPLE} className="h-72 w-full rounded-lg border border-ink-600 bg-ink-950 p-3 font-mono text-[12px] text-fog-100 outline-none focus:border-phoenix-500" />
        {err ? <ErrorBox error={err} /> : null}
        <div className="flex items-center justify-end gap-3">
          {saved && <span className="text-xs text-emerald-300">Saved — new verification runs will use these fixtures.</span>}
          <Button onClick={save} loading={busy}>
            <Save className="h-4 w-4" /> Save fixtures
          </Button>
        </div>
      </div>
    </details>
  );
}
