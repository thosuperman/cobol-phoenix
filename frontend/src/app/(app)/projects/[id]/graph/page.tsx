"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";
import { Background, Controls, Handle, MarkerType, MiniMap, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { BookOpen, Database, ExternalLink, FileCode2, Network, Workflow } from "lucide-react";
import { sourceHref, useProject } from "@/components/project-context";
import { Badge, Card, CardHeader, Chip, EmptyState, ErrorBox, PageLoading, cn } from "@/components/ui";
import { api, type GraphEdge, type GraphNode } from "@/lib/api";
import { useApi } from "@/lib/use-api";

const NODE_STYLE: Record<string, { cls: string; icon: typeof FileCode2; w: number }> = {
  program: { cls: "border-phoenix-500/70 bg-gradient-to-b from-phoenix-500/20 to-ink-850 text-fog-50", icon: FileCode2, w: 190 },
  copybook: { cls: "border-sky-500/60 bg-sky-500/10 text-sky-100", icon: BookOpen, w: 170 },
  paragraph: { cls: "border-ink-500 bg-ink-800 text-fog-200", icon: Workflow, w: 190 },
  record: { cls: "border-emerald-500/50 bg-emerald-500/10 text-emerald-100", icon: Database, w: 190 },
  external: { cls: "border-dashed border-rose-400/60 bg-rose-500/5 text-rose-200", icon: ExternalLink, w: 170 },
  missing: { cls: "border-dashed border-amber-400/60 bg-amber-400/5 text-amber-200", icon: BookOpen, w: 170 },
};

const EDGE_COLOR: Record<string, string> = { call: "#ff8a1f", copy: "#38bdf8", perform: "#6c7584", goto: "#fb7185", contains: "#343d4c", declares: "#34d399", uses: "#2f6b52" };

function GraphNodeView({ data, selected }: NodeProps<Node<{ node: GraphNode }>>) {
  const n = data.node;
  const s = NODE_STYLE[n.type] ?? NODE_STYLE.paragraph;
  const Icon = s.icon;
  return (
    <div className={cn("rounded-lg border px-3 py-2 shadow-lg transition", s.cls, selected && "ring-2 ring-phoenix-400")} style={{ width: s.w }}>
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-ink-500" />
      <div className="flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" />
        <span className="truncate font-mono text-[11.5px] font-medium">{n.label}</span>
      </div>
      <div className="mt-0.5 truncate text-[10px] opacity-60">
        {n.type}
        {n.complexity ? ` · ${n.complexity}` : ""}
        {n.size ? ` · ${n.size} bytes` : ""}
      </div>
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-ink-500" />
    </div>
  );
}

const nodeTypes = { phx: GraphNodeView };

function layout(nodes: GraphNode[], edges: GraphEdge[]) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 18, ranksep: 70 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: (NODE_STYLE[n.type] ?? NODE_STYLE.paragraph).w, height: 46 }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const p = g.node(n.id);
    return { id: n.id, type: "phx", position: { x: p.x - p.width / 2, y: p.y - p.height / 2 }, data: { node: n } } as Node<{ node: GraphNode }>;
  });
}

export default function GraphPage() {
  const { id, analysis } = useProject();
  const graph = useApi(() => api.graph(id), [id]);
  const [showParas, setShowParas] = useState(false);
  const [showRecords, setShowRecords] = useState(false);
  const [focus, setFocus] = useState<string>("");
  const [selected, setSelected] = useState<string | null>(null);

  const view = useMemo(() => {
    if (!graph.data) return null;
    const all = graph.data;
    const keep = new Set<string>();
    for (const n of all.nodes) {
      if (n.type === "paragraph" && !showParas) continue;
      if (n.type === "record" && !showRecords) continue;
      if (focus && (n.type === "paragraph" || n.type === "record") && n.program !== focus) continue;
      keep.add(n.id);
    }
    const nodes = all.nodes.filter((n) => keep.has(n.id));
    const edges = all.edges.filter((e) => keep.has(e.source) && keep.has(e.target) && (e.type !== "contains" || showParas) && (e.type !== "uses" || (showParas && showRecords)));
    const dedup = new Map<string, GraphEdge>();
    edges.forEach((e) => dedup.set(`${e.source}>${e.target}>${e.type}`, e));
    const es = [...dedup.values()];
    const rfNodes = layout(nodes, es);
    const rfEdges: Edge[] = es.map((e, i) => ({
      id: `${e.source}-${e.target}-${e.type}-${i}`,
      source: e.source,
      target: e.target,
      animated: e.type === "call",
      style: { stroke: EDGE_COLOR[e.type] ?? "#6c7584", strokeWidth: e.type === "call" ? 2 : 1.2, strokeDasharray: e.type === "copy" ? "4 3" : undefined },
      markerEnd: { type: MarkerType.ArrowClosed, color: EDGE_COLOR[e.type] ?? "#6c7584", width: 14, height: 14 },
      label: e.type === "call" ? "CALL" : e.type === "copy" ? "COPY" : e.type === "goto" ? "GO TO" : undefined,
      labelStyle: { fill: "#c3c9d2", fontSize: 10 },
      labelBgStyle: { fill: "#0b0d11" },
    }));
    return { nodes: rfNodes, edges: rfEdges, raw: es };
  }, [graph.data, showParas, showRecords, focus]);

  if (graph.error) return <ErrorBox error={graph.error} onRetry={graph.reload} />;
  if (!graph.data || !analysis || !view) return <PageLoading />;
  const sel = selected ? graph.data.nodes.find((n) => n.id === selected) : null;
  const incoming = sel ? graph.data.edges.filter((e) => e.target === sel.id) : [];
  const outgoing = sel ? graph.data.edges.filter((e) => e.source === sel.id) : [];
  const label = (nid: string) => graph.data!.nodes.find((n) => n.id === nid)?.label ?? nid;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <Card className="overflow-hidden">
        <CardHeader
          title="Dependency graph"
          subtitle="Programs, copybooks and CALL relationships. Toggle paragraphs (PERFORM) and data records (read/write usage)."
          icon={<Network className="h-4 w-4" />}
          actions={
            <div className="flex flex-wrap items-center gap-1.5">
              <Chip active={showParas} onClick={() => setShowParas(!showParas)}>
                paragraphs
              </Chip>
              <Chip active={showRecords} onClick={() => setShowRecords(!showRecords)}>
                records
              </Chip>
              <select value={focus} onChange={(e) => setFocus(e.target.value)} className="rounded-md border border-ink-600 bg-ink-900 px-2 py-0.5 text-[11px] text-fog-200">
                <option value="">all programs</option>
                {analysis.programs.map((p) => (
                  <option key={p.program_id} value={p.program_id}>
                    {p.program_id}
                  </option>
                ))}
              </select>
            </div>
          }
        />
        <div className="h-[68vh] bg-ink-950">
          {view.nodes.length === 0 ? (
            <div className="p-6">
              <EmptyState title="Nothing to show" body="Adjust the filters." />
            </div>
          ) : (
            <ReactFlow nodes={view.nodes} edges={view.edges} nodeTypes={nodeTypes} fitView minZoom={0.1} onNodeClick={(_, n) => setSelected(n.id)} onPaneClick={() => setSelected(null)} proOptions={{ hideAttribution: true }}>
              <Background color="#1b2029" gap={24} />
              <Controls showInteractive={false} />
              <MiniMap pannable zoomable maskColor="rgba(7,8,11,0.7)" style={{ background: "#0b0d11" }} nodeColor={(n) => ((n.data as { node: GraphNode }).node.type === "program" ? "#ff8a1f" : "#343d4c")} />
            </ReactFlow>
          )}
        </div>
        <div className="flex flex-wrap gap-3 border-t border-ink-700 px-5 py-2.5 text-[11px] text-fog-500">
          {Object.entries(EDGE_COLOR)
            .filter(([k]) => k !== "contains")
            .map(([k, c]) => (
              <span key={k} className="flex items-center gap-1.5">
                <span className="h-0.5 w-4" style={{ background: c }} /> {k}
              </span>
            ))}
        </div>
      </Card>
      <Card className="h-fit xl:sticky xl:top-6">
        <CardHeader title="Inspector" subtitle={sel ? sel.type : "Select a node to see its source references"} />
        {!sel ? (
          <div className="space-y-2 p-5 text-sm text-fog-400">
            <p>
              {graph.data.nodes.filter((n) => n.type === "program").length} programs, {graph.data.nodes.filter((n) => n.type === "copybook").length} copybooks,{" "}
              {graph.data.edges.filter((e) => e.type === "call").length} CALL edges, {graph.data.edges.filter((e) => e.type === "perform").length} PERFORM edges.
            </p>
            <p className="text-xs text-fog-500">Every edge carries the file and line of the statement that created it.</p>
          </div>
        ) : (
          <div className="space-y-4 p-5 text-sm">
            <div>
              <div className="font-mono text-base text-fog-50">{sel.label}</div>
              {sel.file && (
                <Link href={sourceHref(id, sel.file, sel.line ?? undefined, sel.end_line)} className="mt-1 inline-flex items-center gap-1 font-mono text-xs text-phoenix-300 hover:underline">
                  {sel.file}:{sel.line}
                  {sel.end_line ? `-${sel.end_line}` : ""} <ExternalLink className="h-3 w-3" />
                </Link>
              )}
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge>{sel.type}</Badge>
                {sel.complexity && <Badge tone="phoenix">complexity {sel.complexity}</Badge>}
                {sel.section && <Badge tone="green">{sel.section}</Badge>}
              </div>
            </div>
            {[
              { t: "Incoming", list: incoming, other: (e: GraphEdge) => e.source },
              { t: "Outgoing", list: outgoing, other: (e: GraphEdge) => e.target },
            ].map((grp) => (
              <div key={grp.t}>
                <div className="mb-1.5 text-[11px] uppercase tracking-wider text-fog-500">
                  {grp.t} ({grp.list.length})
                </div>
                <div className="max-h-56 space-y-1 overflow-y-auto">
                  {grp.list.slice(0, 60).map((e, i) => (
                    <Link key={i} href={sourceHref(id, e.file, e.line)} className="flex items-center gap-2 rounded-md px-2 py-1 text-xs hover:bg-ink-800">
                      <span className="w-14 shrink-0 font-mono uppercase" style={{ color: EDGE_COLOR[e.type] }}>
                        {e.type}
                        {e.mode ? `:${e.mode}` : ""}
                      </span>
                      <span className="truncate font-mono text-fog-200">{label(grp.other(e))}</span>
                      <span className="ml-auto shrink-0 font-mono text-fog-500">:{e.line}</span>
                    </Link>
                  ))}
                  {grp.list.length === 0 && <div className="px-2 text-xs text-fog-500">none</div>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
