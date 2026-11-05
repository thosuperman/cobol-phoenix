"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { Analysis } from "@/lib/api";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";

interface Ctx {
  id: string;
  analysis: Analysis | undefined;
  error: unknown;
  loading: boolean;
  reload: () => void;
}

const ProjectCtx = createContext<Ctx | null>(null);

export function ProjectProvider({ id, children }: { id: string; children: ReactNode }) {
  const { data, error, loading, reload } = useApi(() => api.analysis(id), [id]);
  return <ProjectCtx.Provider value={{ id, analysis: data, error, loading, reload }}>{children}</ProjectCtx.Provider>;
}

export function useProject(): Ctx {
  const c = useContext(ProjectCtx);
  if (!c) throw new Error("useProject outside ProjectProvider");
  return c;
}

export function sourceHref(id: string, file: string, line?: number, end?: number) {
  const q = new URLSearchParams({ file });
  if (line) q.set("line", String(line));
  if (end) q.set("end", String(end));
  return `/projects/${id}/source?${q.toString()}`;
}
