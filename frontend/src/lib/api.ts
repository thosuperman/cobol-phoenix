// Typed client for the COBOL Phoenix backend. All data shown in the UI comes from here.

export type Status = "VERIFIED" | "FAILED" | "NOT_VERIFIABLE" | "UNSUPPORTED" | "NOT_EXERCISED" | "NOT_RUN" | "EXTRACTED";

export interface Overview {
  programs: number;
  copybooks: number;
  source_files: number;
  source_lines: number;
  dependencies: number;
  call_edges: number;
  copy_edges: number;
  business_rules: number;
  unsupported_constructs: number;
  unsupported_by_construct: Record<string, number>;
  errors: number;
  warnings: number;
  complexity_score: number;
  complexity_band: string;
  complexity_weights: Record<string, number>;
  missing_copybooks: string[];
  external_calls: string[];
}

export interface Project {
  id: string;
  name: string;
  description: string;
  source_kind: string;
  source_ref: string;
  license: string;
  format_override: string | null;
  file_count: number;
  line_count: number;
  created_at: string;
  analyzed_at: string | null;
  overview: Overview | null;
  import_report: { stored?: number; skipped?: { path: string; reason: string }[]; skipped_count?: number; license?: string };
  latest_verification?: (RunSummary & { entry: string; run_id: string }) | null;
  generations?: number;
}

export interface Metrics {
  statements: number;
  decision_points: number;
  paragraphs: number;
  calls: number;
  unsupported: number;
  data_items: number;
  cyclomatic: number;
  score: number;
  band: string;
}

export interface ProgramInfo {
  program_id: string;
  file: string;
  line_start: number;
  line_end: number;
  source_format: string;
  kind: "main" | "subprogram";
  using: string[];
  paragraphs: { name: string; section: string | null; line_start: number; line_end: number; statements: number }[];
  copybooks: string[];
  calls: { target: string; file: string; line: number; paragraph: string }[];
  files: { name: string; assign: string; organization: string; line: number }[];
  records: { name: string; level: number; section: string; size: number; file: string; line: number; fields: number; read: number; written: number }[];
  metrics: Metrics;
  rules: number;
  unsupported: number;
  errors: number;
  warnings: number;
}

export interface Unsupported {
  construct: string;
  category: string;
  reason: string;
  file: string;
  line: number;
  end_line: number;
  text: string;
  program: string;
}

export interface Diagnostic {
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
  file: string;
  line: number;
  program?: string;
}

export interface Analysis {
  project: Project;
  overview: Overview;
  programs: ProgramInfo[];
  unsupported: Unsupported[];
  diagnostics: Diagnostic[];
  files: { path: string; kind: string; format: string; lines: number }[];
}

export interface GraphNode {
  id: string;
  type: "program" | "copybook" | "paragraph" | "record" | "external" | "missing";
  label: string;
  file: string | null;
  line: number | null;
  end_line?: number;
  program?: string;
  complexity?: string;
  score?: number;
  section?: string;
  size?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "copy" | "call" | "contains" | "perform" | "goto" | "declares" | "uses";
  file: string;
  line: number;
  mode?: string;
  thru?: string | null;
}

export interface Rule {
  id: string;
  name: string;
  description: string;
  description_source: "source-comment" | "deterministic";
  program: string;
  paragraph: string;
  file: string;
  line_start: number;
  line_end: number;
  inputs: string[];
  outputs: string[];
  conditions: { text: string; line: number; end_line: number }[];
  calculations: { text: string; line: number; end_line: number }[];
  assignments: { text: string; line: number }[];
  decision_tables: { subject: string; line: number; end_line: number; rows: { when: string; actions: string[]; line: number }[] }[];
  related_paragraphs: string[];
  statement_keys: string[];
  unsupported: { construct: string; line: number; reason: string }[];
  status: string;
  annotation?: string;
  verification: { status: Status; statements: number; executed: number; coverage_pct: number; failing_cases?: number };
}

export interface Explanation {
  rule_id: string;
  text: string;
  provider: string;
  model: string | null;
  advisory: boolean;
  evidence: { file: string; line_start: number; line_end: number };
}

export interface Mutation {
  id: string;
  kind: "rounding" | "relop" | "arith" | "literal";
  file: string;
  line: number;
  detail: string;
  ordinal: number;
}

export interface GenerationSummary {
  entry: string;
  mode: "linkage" | "main";
  call_tree: string[];
  files: string[];
  statements: number;
  unsupported: { construct: string; file: string; line: number; reason: string; program: string }[];
  modules: { program: string; module: string; class: string; statements: number }[];
  endpoint: string;
  fixtures: number;
  mutation: Mutation | null;
  lines_of_code: number;
}

export interface Generation {
  id: string;
  project_id: string;
  entry: string;
  name: string;
  mutation_id: string | null;
  mutation_detail: string | null;
  created_at: string;
  summary: GenerationSummary;
}

export interface InterfaceNode {
  name: string;
  py: string;
  attr: string;
  kind?: string;
  size?: number;
  digits?: number;
  scale?: number;
  signed?: boolean;
  picture?: string;
  role?: string;
  loc: string;
  occurs?: number;
  children?: InterfaceNode[];
}

export interface GenerationDetail extends Generation {
  interface: { entry: string; mode: string; params: { name: string; py: string; size: number; display_only: boolean; inputs: InterfaceNode[]; outputs: InterfaceNode[] }[] };
  schemas: string;
}

export interface TraceEntry {
  python_file: string;
  python_start: number;
  python_end: number;
  cobol_file: string;
  cobol_start: number;
  cobol_end: number;
  construct: string;
  paragraph: string;
  program: string;
}

export interface RunSummary {
  total: number;
  verified: number;
  failed: number;
  not_verifiable: number;
  unsupported: number;
  statements_total: number;
  statements_executed: number;
  coverage_pct: number;
  by_kind: Record<string, Record<string, number>>;
}

export interface Diff {
  param: string;
  field: string;
  cobol: string | null;
  python: string | null;
  loc?: string;
  kind?: string;
  cobol_value?: string;
  python_value?: string;
  delta?: string;
  note?: string;
}

export interface CaseResult {
  id: string;
  kind: string;
  description: string;
  status: Status;
  note: string;
  inputs: Record<string, Record<string, string>>;
  stdin: string;
  cobol: { stdout: string; stderr: string; rc: number | null; timed_out: boolean; duration_ms: number } | null;
  python: { stdout: string; status: string; error: string | null };
  diffs: Diff[];
  executed: string[];
}

export interface Report {
  entry: string;
  mode: "harness" | "main";
  fixed_datetime: string;
  duration_s: number;
  executor: { name: string; available: boolean; error: string | null; cobc_version: string };
  compile: { ok: boolean; command: string; log: string };
  summary: RunSummary;
  statements: { key: string; file: string; line: number; end_line: number; construct: string; paragraph: string; program: string; python_file: string; python_line: number; passed: number; failed: number; other: number }[];
  cases: CaseResult[];
  claim: string;
  mutation: Mutation | null;
  generation_id: string;
}

export interface MutationResult {
  candidates: number;
  evaluated: number;
  killed: number;
  survived: number;
  score_pct: number;
  reference: string;
  mutants: (Mutation & { status: "killed" | "survived" | "not-applied"; killed_by?: string[] })[];
}

export interface Run {
  id: string;
  generation_id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "error";
  progress: string;
  with_mutation: boolean;
  created_at: string;
  finished_at: string | null;
  summary: Partial<RunSummary>;
  error: string | null;
  entry?: string;
  mutation_id?: string | null;
  mutation_detail?: string | null;
  report?: Report | null;
  mutation?: MutationResult | null;
}

export interface Health {
  status: string;
  version: string;
  executor: { name: string; available: boolean; detail: string };
  llm: { provider: string };
}

export interface Dashboard {
  totals: { projects: number; programs: number; rules: number; generations: number; runs: number; cases_verified: number; cases_failed: number };
  projects: Project[];
  recent_runs: (Run & { entry: string; project_name: string })[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/health"),
  dashboard: () => request<Dashboard>("/dashboard"),
  projects: () => request<Project[]>("/projects"),
  project: (id: string) => request<Project>(`/projects/${id}`),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: "DELETE" }),
  importSample: () => request<Project>("/projects/sample", { method: "POST" }),
  importGithub: (body: { repo: string; ref?: string; name?: string; subdir?: string; source_format?: string }) => request<Project>("/projects/github", json(body)),
  importLocal: (body: { path: string; name?: string; source_format?: string }) => request<Project>("/projects/local", json(body)),
  upload: (files: File[], name: string, sourceFormat: string) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f, f.name));
    fd.append("name", name);
    fd.append("source_format", sourceFormat);
    return request<Project>("/projects/upload", { method: "POST", body: fd });
  },
  analyze: (id: string) => request<Project>(`/projects/${id}/analyze`, { method: "POST" }),
  analysis: (id: string) => request<Analysis>(`/projects/${id}/analysis`),
  graph: (id: string) => request<{ nodes: GraphNode[]; edges: GraphEdge[] }>(`/projects/${id}/graph`),
  file: (id: string, path: string) => request<{ path: string; text: string; lines: number }>(`/projects/${id}/files/content?path=${encodeURIComponent(path)}`),
  rules: (id: string) => request<Rule[]>(`/projects/${id}/rules`),
  explain: (id: string, ruleId: string) => request<Explanation>(`/projects/${id}/rules/${encodeURIComponent(ruleId)}/explain`, { method: "POST" }),
  fixtures: (id: string) => request<Record<string, unknown[]>>(`/projects/${id}/fixtures`),
  saveFixtures: (id: string, body: unknown) => request<Record<string, unknown[]>>(`/projects/${id}/fixtures`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  mutations: (id: string, program: string) => request<Mutation[]>(`/projects/${id}/programs/${program}/mutations`),
  generate: (id: string, body: { entry: string; name?: string; mutation_id?: string }) => request<Generation>(`/projects/${id}/generations`, json(body)),
  generations: (id: string) => request<Generation[]>(`/projects/${id}/generations`),
  generation: (gid: string) => request<GenerationDetail>(`/generations/${gid}`),
  generationFile: (gid: string, path: string) => request<{ path: string; text: string }>(`/generations/${gid}/file?path=${encodeURIComponent(path)}`),
  traceability: (gid: string) => request<TraceEntry[]>(`/generations/${gid}/traceability`),
  verify: (gid: string, mutationAnalysis: boolean) => request<Run>(`/generations/${gid}/verify`, json({ mutation_analysis: mutationAnalysis })),
  run: (rid: string) => request<Run>(`/runs/${rid}`),
  runs: (id: string) => request<Run[]>(`/projects/${id}/runs`),
  exportUrl: (id: string, kind: string, params?: Record<string, string>) => `/api/projects/${id}/export/${kind}${params ? "?" + new URLSearchParams(params).toString() : ""}`,
  downloadUrl: (gid: string) => `/api/generations/${gid}/download`,
};
