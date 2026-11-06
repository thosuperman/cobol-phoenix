"use client";

import Link from "next/link";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

export function cn(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

export function Card({ className, children, ...rest }: ComponentProps<"div">) {
  return (
    <div className={cn("min-w-0 rounded-xl border border-ink-600/70 bg-ink-850/80 backdrop-blur-sm", className)} {...rest}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, icon, actions }: { title: ReactNode; subtitle?: ReactNode; icon?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-ink-600/60 px-5 py-4">
      <div className="flex items-start gap-3">
        {icon && <div className="mt-0.5 text-phoenix-400">{icon}</div>}
        <div>
          <h3 className="text-sm font-semibold text-fog-50">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-fog-400">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex max-w-full flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-gradient-to-b from-phoenix-400 to-phoenix-600 text-ink-950 font-semibold hover:from-phoenix-300 hover:to-phoenix-500 shadow-[0_8px_24px_-10px_rgba(255,138,31,0.6)]",
  secondary: "border border-ink-500 bg-ink-800 text-fog-100 hover:border-ink-500 hover:bg-ink-700",
  ghost: "text-fog-300 hover:bg-ink-800 hover:text-fog-50",
  danger: "border border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20",
};

export function Button({ variant = "secondary", loading, className, children, disabled, ...rest }: ComponentProps<"button"> & { variant?: ButtonVariant; loading?: boolean }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function LinkButton({ href, variant = "secondary", className, children, ...rest }: ComponentProps<typeof Link> & { variant?: ButtonVariant }) {
  return (
    <Link href={href} className={cn("inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm transition", variants[variant], className)} {...rest}>
      {children}
    </Link>
  );
}

export function Badge({ children, tone = "neutral", className }: { children: ReactNode; tone?: "neutral" | "phoenix" | "green" | "red" | "amber" | "blue" | "violet"; className?: string }) {
  const tones = {
    neutral: "border-ink-500 bg-ink-700/60 text-fog-300",
    phoenix: "border-phoenix-500/40 bg-phoenix-500/10 text-phoenix-300",
    green: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
    red: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    amber: "border-amber-400/40 bg-amber-400/10 text-amber-200",
    blue: "border-sky-500/40 bg-sky-500/10 text-sky-300",
    violet: "border-violet-500/40 bg-violet-500/10 text-violet-300",
  };
  return <span className={cn("inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium tracking-wide", tones[tone], className)}>{children}</span>;
}

export function StatTile({ label, value, hint, icon, accent }: { label: string; value: ReactNode; hint?: ReactNode; icon?: ReactNode; accent?: boolean }) {
  return (
    <Card className={cn("relative overflow-hidden px-4 py-3.5", accent && "glow-phoenix")}>
      <div className="flex items-center justify-between gap-1.5 text-[10.5px] uppercase tracking-wide text-fog-400">
        <span className="truncate">{label}</span>
        {icon && <span className="shrink-0 text-fog-500">{icon}</span>}
      </div>
      <div className={cn("mt-1.5 text-2xl font-semibold tabular-nums", accent ? "text-phoenix-300" : "text-fog-50")}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-fog-500">{hint}</div>}
    </Card>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-fog-400">
      <Loader2 className="h-4 w-4 animate-spin text-phoenix-400" />
      {label ?? "Loading"}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-ink-700/60", className)} />;
}

export function PageLoading({ label }: { label?: string }) {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-72" />
      <span className="sr-only">{label ?? "Loading"}</span>
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/5 p-4 text-sm text-rose-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">
        <div className="font-medium">Something went wrong</div>
        <div className="mt-1 break-words text-rose-300/80">{msg}</div>
      </div>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, body, action, icon }: { title: string; body?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="grid-bg flex flex-col items-center justify-center rounded-xl border border-dashed border-ink-500 px-6 py-14 text-center">
      <div className="mb-3 text-fog-500">{icon ?? <Inbox className="h-8 w-8" />}</div>
      <div className="font-medium text-fog-100">{title}</div>
      {body && <div className="mt-1 max-w-md text-sm text-fog-400">{body}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function PageTitle({ title, subtitle, actions, eyebrow }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.2em] text-phoenix-400">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-fog-50">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-fog-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Chip({ children, onClick, active }: { children: ReactNode; onClick?: () => void; active?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md border px-2 py-0.5 font-mono text-[11px] transition",
        active ? "border-phoenix-500/60 bg-phoenix-500/15 text-phoenix-200" : "border-ink-500 bg-ink-800 text-fog-300 hover:border-ink-500 hover:text-fog-50",
      )}
    >
      {children}
    </button>
  );
}

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: ReactNode }[]; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-lg border border-ink-600 bg-ink-900 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={cn("rounded-md px-3 py-1 text-xs transition", value === o.value ? "bg-ink-700 text-fog-50" : "text-fog-400 hover:text-fog-100")}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
