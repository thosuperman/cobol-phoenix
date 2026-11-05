import { CheckCircle2, CircleDashed, CircleSlash, HelpCircle, Ban, XCircle, FileSearch } from "lucide-react";
import type { Status } from "@/lib/api";
import { cn } from "./ui";

export const STATUS_META: Record<string, { label: string; cls: string; dot: string; icon: typeof CheckCircle2; help: string }> = {
  VERIFIED: { label: "VERIFIED", cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300", dot: "#34d399", icon: CheckCircle2, help: "GnuCOBOL and Python both ran and produced identical outputs" },
  FAILED: { label: "FAILED", cls: "border-rose-500/40 bg-rose-500/10 text-rose-300", dot: "#fb7185", icon: XCircle, help: "Both ran and at least one output field differs" },
  NOT_VERIFIABLE: { label: "NOT VERIFIABLE", cls: "border-amber-400/40 bg-amber-400/10 text-amber-200", dot: "#fbbf24", icon: HelpCircle, help: "The original COBOL could not be executed; nothing was compared" },
  UNSUPPORTED: { label: "UNSUPPORTED", cls: "border-violet-500/40 bg-violet-500/10 text-violet-300", dot: "#a78bfa", icon: Ban, help: "Contains or executed a construct outside the supported subset" },
  NOT_EXERCISED: { label: "NOT EXERCISED", cls: "border-ink-500 bg-ink-700/60 text-fog-400", dot: "#6c7584", icon: CircleDashed, help: "No differential case executed this rule" },
  NOT_RUN: { label: "NOT RUN", cls: "border-ink-500 bg-ink-700/60 text-fog-400", dot: "#6c7584", icon: CircleSlash, help: "No verification run yet" },
  EXTRACTED: { label: "EXTRACTED", cls: "border-sky-500/40 bg-sky-500/10 text-sky-300", dot: "#38bdf8", icon: FileSearch, help: "Extracted deterministically; not yet verified" },
};

export function StatusBadge({ status, className, compact }: { status: Status | string; className?: string; compact?: boolean }) {
  const m = STATUS_META[status] ?? STATUS_META.NOT_RUN;
  const Icon = m.icon;
  return (
    <span title={m.help} className={cn("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10.5px] font-semibold tracking-wider whitespace-nowrap", m.cls, className)}>
      <Icon className="h-3 w-3" />
      {!compact && m.label}
    </span>
  );
}

export function bandTone(band: string): string {
  return { Low: "text-emerald-300", Medium: "text-amber-200", High: "text-phoenix-300", "Very High": "text-rose-300" }[band] ?? "text-fog-300";
}
