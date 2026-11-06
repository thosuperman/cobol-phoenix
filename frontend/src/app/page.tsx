import Link from "next/link";
import { ArrowRight, Binary, FileSearch, FlaskConical, GitCompareArrows, Network, ShieldCheck, Sparkles, Workflow } from "lucide-react";
import { PhoenixMark, Wordmark } from "@/components/logo";

const ACTS = [
  {
    n: "I",
    title: "The dead system",
    icon: Binary,
    body: "Decades of insurance and banking rules live in COBOL nobody wants to touch. The logic is valuable; the documentation is gone.",
  },
  {
    n: "II",
    title: "The discovery",
    icon: FileSearch,
    body: "A deterministic parser builds an intermediate representation, a dependency graph and business rules — every one cited to a real file and line range.",
  },
  {
    n: "III",
    title: "The resurrection",
    icon: Sparkles,
    body: "Template-based generation turns a COBOL capability into a typed Python module and FastAPI endpoint, with Decimal arithmetic and line-level traceability.",
  },
  {
    n: "IV",
    title: "The proof",
    icon: GitCompareArrows,
    body: "The original program runs in a sandboxed GnuCOBOL container next to the generated Python. Identical inputs, field-by-field comparison, mutation analysis.",
  },
];

const PIPELINE = ["COBOL source", "Lexer + COPY", "Parser", "Normalized IR", "Rules + graph", "Python generator", "FastAPI service", "Differential tests"];

export default function Landing() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="grid-bg pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]" />
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-phoenix-600/15 blur-[120px]" />
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Wordmark id="phx-g-landing" />
        <nav className="flex items-center gap-2 text-sm">
          <Link href="/import" className="hidden rounded-lg px-3 py-2 text-fog-300 hover:text-fog-50 sm:block">
            Import COBOL
          </Link>
          <Link href="/dashboard" className="rounded-lg border border-ink-500 bg-ink-800/80 px-3.5 py-2 text-fog-100 hover:bg-ink-700">
            Open workspace
          </Link>
        </nav>
      </header>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pt-14 pb-20 text-center sm:pt-24">
        <div className="animate-fade-up mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-phoenix-500/30 bg-phoenix-500/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.2em] text-phoenix-300">
          <span className="animate-ember h-1.5 w-1.5 rounded-full bg-phoenix-400" /> Mainframe resurrection laboratory
        </div>
        <h1 className="animate-fade-up mx-auto max-w-4xl text-4xl font-semibold tracking-tight text-fog-50 sm:text-6xl">
          From Mainframe to Modern.
          <br />
          <span className="text-gradient-phoenix">Preserve the logic. Rebuild the future.</span>
        </h1>
        <p className="animate-fade-up mx-auto mt-6 max-w-2xl text-base text-fog-300 sm:text-lg">
          COBOL Phoenix turns COBOL business logic into Python APIs — and proves it. Every rule is backed by source evidence, every generated statement traces back to its
          COBOL line, and behaviour is verified against the original program running in GnuCOBOL.
        </p>
        <div className="animate-fade-up mt-9 flex flex-wrap items-center justify-center gap-3">
          <Link href="/import" className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-b from-phoenix-400 to-phoenix-600 px-5 py-2.5 text-sm font-semibold text-ink-950 shadow-[0_10px_30px_-10px_rgba(255,138,31,0.7)] hover:from-phoenix-300">
            Start with the sample project <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/dashboard" className="rounded-lg border border-ink-500 bg-ink-850 px-5 py-2.5 text-sm text-fog-100 hover:bg-ink-700">
            Go to dashboard
          </Link>
        </div>

        <div className="relative mx-auto mt-16 max-w-4xl overflow-hidden rounded-xl border border-ink-600 bg-ink-900/90 text-left shadow-2xl">
          <div className="flex items-center gap-1.5 border-b border-ink-700 px-4 py-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-ink-500" />
            <span className="h-2.5 w-2.5 rounded-full bg-ink-500" />
            <span className="h-2.5 w-2.5 rounded-full bg-ink-500" />
            <span className="ml-3 font-mono text-[11px] text-fog-500">RATEENG.cbl → app/programs/rateeng.py</span>
          </div>
          <div className="grid font-mono text-[12px] leading-6 md:grid-cols-2">
            <pre className="scanlines overflow-x-auto border-b border-ink-700 p-4 text-fog-300 md:border-r md:border-b-0">
              <span className="text-fog-500">{"      * PM-404: Base premium.\n"}</span>
              <span className="text-phoenix-300">{"           COMPUTE "}</span>
              {"RR-BASE-PREMIUM "}
              <span className="text-phoenix-300">ROUNDED</span>
              {" =\n                   WS-BASE-RATE * RR-AGE-FACTOR\n                 * WS-VEH-FACTOR * WS-COV-FACTOR\n                 * WS-DED-FACTOR + WS-VALUE-LOAD\n"}
              <span className="text-phoenix-300">{"              ON SIZE ERROR\n"}</span>
              {"                 SET RR-INVALID TO TRUE"}
            </pre>
            <pre className="overflow-x-auto p-4 text-fog-300">
              <span className="text-fog-500">{"# cobol/RATEENG.cbl:198-206\n"}</span>
              {"_size_error = False\n_v = (((self.ws_base_rate.value * ...)\n"}
              <span className="text-fog-500">{"     # Decimal, 64-digit context\n"}</span>
              {"if not self.rr_base_premium.store(\n        _v, rounded=True, size_error=True):\n    _size_error = True\n"}
              <span className="text-emerald-300">{"# sample run: 127/127 cases identical to GnuCOBOL 3.2"}</span>
            </pre>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-20">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {ACTS.map((a) => (
            <div key={a.n} className="rounded-xl border border-ink-600/70 bg-ink-850/70 p-5">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs tracking-[0.25em] text-phoenix-400">ACT {a.n}</span>
                <a.icon className="h-4 w-4 text-fog-500" />
              </div>
              <h3 className="mt-3 font-semibold text-fog-50">{a.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-fog-400">{a.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-20">
        <h2 className="text-center text-sm font-semibold uppercase tracking-[0.2em] text-fog-400">Understand first, generate second, prove always</h2>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {PIPELINE.map((p, i) => (
            <div key={p} className="flex items-center gap-2">
              <span className="rounded-lg border border-ink-600 bg-ink-850 px-3 py-1.5 font-mono text-xs text-fog-200">{p}</span>
              {i < PIPELINE.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-phoenix-500" />}
            </div>
          ))}
        </div>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {[
            { icon: Network, t: "No AI guesswork in the core", b: "Parsing, rule extraction and code generation are deterministic. Optional LLM explanations are labelled advisory and never alter evidence." },
            { icon: FlaskConical, t: "Differential verification", b: "Boundary values derived from the IR, edge cases and seeded random records run through both runtimes. Mutation analysis measures how strong the suite is." },
            { icon: ShieldCheck, t: "Sandboxed by design", b: "Uploaded code is data. COBOL only runs in a network-less, resource-limited GnuCOBOL container; if it can’t run, results say NOT_VERIFIABLE." },
          ].map((f) => (
            <div key={f.t} className="rounded-xl border border-ink-600/70 bg-ink-850/70 p-5">
              <f.icon className="h-5 w-5 text-phoenix-400" />
              <h3 className="mt-3 font-semibold text-fog-50">{f.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-fog-400">{f.b}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="relative z-10 border-t border-ink-700">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-6 text-xs text-fog-500">
          <span className="flex items-center gap-2">
            <PhoenixMark className="h-5 w-5" gradientId="phx-g-footer" /> COBOL Phoenix · Apache-2.0 · Built for Kiroween 2026
          </span>
          <span className="flex items-center gap-1.5">
            <Workflow className="h-3.5 w-3.5" /> COBOL → IR → Python → proof
          </span>
        </div>
      </footer>
    </div>
  );
}
