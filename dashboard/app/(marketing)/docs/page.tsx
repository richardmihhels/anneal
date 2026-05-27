import type { Metadata } from "next";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export const metadata: Metadata = {
  title: "Docs — Anneal",
  description: "Anneal SDK reference, quick start, and core concepts.",
};

const SDK_INSTALL = `pip install anneal-sdk`;

const SDK_QUICKSTART = `from anneal import trace, AnnealClient

# Initialize once at startup
client = AnnealClient(
    org_id=os.environ["ANNEAL_ORG_ID"],
    api_key=os.environ["ANNEAL_API_KEY"],
    endpoint=os.environ["ANNEAL_ENDPOINT"],
)

# Wrap your LangGraph agent
@trace(agent_id="support-v2", client=client)
async def run_agent(input: str) -> str:
    # Your existing LangGraph code — unchanged
    result = await graph.ainvoke({"input": input})
    return result["output"]`;

const TRACE_SCHEMA = `{
  "trace_id": "tr_01HX...",         // auto-generated
  "session_id": "sess_...",          // your conversation ID
  "agent_id": "support-v2",
  "organization_id": "org_...",
  "spans": [
    {
      "span_id": "sp_...",
      "name": "llm.completion",
      "input": "...",
      "output": "...",
      "start_time": "2026-05-01T09:00:00Z",
      "duration_ms": 342
    }
  ],
  "outcome": "resolved" | "escalated" | "unknown"
}`;

const OTEL_EXAMPLE = `from opentelemetry import trace as otel_trace
from anneal.otel import AnnealExporter

# Add Anneal as an OTLP exporter alongside your existing setup
exporter = AnnealExporter(
    endpoint=os.environ["ANNEAL_ENDPOINT"],
    org_id=os.environ["ANNEAL_ORG_ID"],
    api_key=os.environ["ANNEAL_API_KEY"],
)`;

interface Section {
  id: string;
  title: string;
}

const TOC: Section[] = [
  { id: "quickstart", title: "Quick start" },
  { id: "installation", title: "Installation" },
  { id: "instrument", title: "Instrument your agent" },
  { id: "otel", title: "OpenTelemetry" },
  { id: "concepts", title: "Core concepts" },
  { id: "traces", title: "Traces and spans" },
  { id: "eval-gate", title: "The eval gate" },
  { id: "pr-format", title: "The PR format" },
  { id: "reference", title: "SDK reference" },
  { id: "trace-decorator", title: "@trace decorator" },
  { id: "schema", title: "Trace schema" },
];

export default function DocsPage() {
  return (
    <>
      <MarketingNav />

      <div className="mx-auto max-w-5xl px-5 pb-24 pt-28">
        <div className="lg:grid lg:grid-cols-[220px_1fr] lg:gap-12">
          {/* Sidebar TOC */}
          <aside className="hidden lg:block">
            <nav
              aria-label="Documentation navigation"
              className="sticky top-24"
            >
              <p className="mb-3 font-mono text-[10px] font-medium uppercase tracking-widest text-[#B5B4AE]">
                On this page
              </p>
              <ul className="space-y-0.5" role="list">
                {TOC.map((item) => (
                  <li key={item.id}>
                    <a
                      href={`#${item.id}`}
                      className="block rounded py-1 pl-2 text-sm text-[#78776C] transition-colors hover:text-[#111110] focus:outline-none focus:underline"
                    >
                      {item.title}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>

          {/* Content */}
          <article className="min-w-0">
            {/* Page header */}
            <header className="mb-12 border-b border-[#E3E2DA] pb-10">
              <p className="mb-3 font-mono text-xs font-medium uppercase tracking-widest text-[#B5B4AE]">
                Documentation
              </p>
              <h1 className="mb-4 text-3xl font-semibold tracking-tight text-[#111110] sm:text-4xl">
                Getting started
              </h1>
              <p className="text-base leading-relaxed text-[#78776C]">
                Anneal instruments your existing LangGraph agent without
                changing your logic. Traces flow in, the weekly optimization
                job runs, and a PR appears in your repo if something is worth
                shipping.
              </p>
            </header>

            {/* Quick start */}
            <section id="quickstart" aria-labelledby="quickstart-heading" className="mb-14 scroll-mt-24">
              <h2
                id="quickstart-heading"
                className="mb-6 text-xl font-semibold tracking-tight text-[#111110]"
              >
                Quick start
              </h2>

              <ol className="space-y-8" role="list">
                <li>
                  <h3 id="installation" className="mb-3 font-semibold text-[#111110] scroll-mt-24">
                    1. Install the SDK
                  </h3>
                  <CodeBlock lang="bash" code={SDK_INSTALL} />
                </li>
                <li>
                  <h3 id="instrument" className="mb-3 font-semibold text-[#111110] scroll-mt-24">
                    2. Instrument your agent
                  </h3>
                  <p className="mb-3 text-sm leading-relaxed text-[#78776C]">
                    Wrap your agent entrypoint with the{" "}
                    <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">
                      @trace
                    </code>{" "}
                    decorator. Your existing LangGraph code is unchanged.
                  </p>
                  <CodeBlock lang="python" code={SDK_QUICKSTART} />
                </li>
                <li>
                  <h3 className="mb-3 font-semibold text-[#111110]">
                    3. Connect your GitHub repo
                  </h3>
                  <p className="text-sm leading-relaxed text-[#78776C]">
                    Install the Anneal GitHub App on the repo that contains
                    your agent prompt. Anneal will open PRs against that repo&rsquo;s
                    default branch once a week when an improvement clears the
                    eval gate.
                  </p>
                  <div className="mt-3 rounded-lg border border-[#E3E2DA] bg-[#FAFAF8] px-4 py-3 text-sm text-[#78776C]">
                    GitHub App install link is provided in the{" "}
                    <a
                      href="/app/connect"
                      className="text-[#2450B0] underline underline-offset-2 hover:no-underline"
                    >
                      dashboard → Connect
                    </a>{" "}
                    screen.
                  </div>
                </li>
              </ol>
            </section>

            {/* OpenTelemetry */}
            <section id="otel" aria-labelledby="otel-heading" className="mb-14 scroll-mt-24">
              <h2
                id="otel-heading"
                className="mb-3 text-xl font-semibold tracking-tight text-[#111110]"
              >
                OpenTelemetry
              </h2>
              <p className="mb-4 text-sm leading-relaxed text-[#78776C]">
                If you already emit OTLP traces, add Anneal as an additional
                exporter. No SDK decorator needed.
              </p>
              <CodeBlock lang="python" code={OTEL_EXAMPLE} />
            </section>

            <hr className="my-14 border-[#E3E2DA]" />

            {/* Core concepts */}
            <section id="concepts" aria-labelledby="concepts-heading" className="mb-14 scroll-mt-24">
              <h2
                id="concepts-heading"
                className="mb-8 text-2xl font-semibold tracking-tight text-[#111110]"
              >
                Core concepts
              </h2>

              <div className="space-y-10">
                <div id="traces" className="scroll-mt-24">
                  <h3 className="mb-2 text-base font-semibold text-[#111110]">
                    Traces and spans
                  </h3>
                  <p className="text-sm leading-relaxed text-[#78776C]">
                    A <strong className="font-medium text-[#444440]">trace</strong> is one
                    complete conversation between a user and your agent. A{" "}
                    <strong className="font-medium text-[#444440]">span</strong> is one
                    step inside that conversation—an LLM call, a tool
                    invocation, a retrieval. Anneal stores spans in ClickHouse
                    and uses them to compute failure clusters.
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-[#78776C]">
                    Each trace has an{" "}
                    <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">
                      outcome
                    </code>{" "}
                    field:{" "}
                    <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">
                      resolved
                    </code>
                    ,{" "}
                    <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">
                      escalated
                    </code>
                    , or{" "}
                    <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">
                      unknown
                    </code>
                    . Failure clustering focuses on{" "}
                    <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">
                      escalated
                    </code>{" "}
                    traces by default.
                  </p>
                </div>

                <div id="eval-gate" className="scroll-mt-24">
                  <h3 className="mb-2 text-base font-semibold text-[#111110]">
                    The eval gate
                  </h3>
                  <p className="text-sm leading-relaxed text-[#78776C]">
                    Before a prompt mutation can become a PR, it must beat the
                    current baseline on a{" "}
                    <strong className="font-medium text-[#444440]">
                      held-out eval set
                    </strong>{" "}
                    (p&nbsp;&lt;&nbsp;0.05, one-sided). The holdout set is
                    split once per week from incoming traces and is never used
                    during optimization—it cannot be overfit.
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-[#78776C]">
                    The judge is an LLM-as-judge calibrated against a
                    human-labeled seed set. Calibration agreement rate is
                    logged on every run and visible in the dashboard. If
                    agreement drops below 80%, the run is flagged for review.
                  </p>
                </div>

                <div id="pr-format" className="scroll-mt-24">
                  <h3 className="mb-2 text-base font-semibold text-[#111110]">
                    The PR format
                  </h3>
                  <p className="text-sm leading-relaxed text-[#78776C]">
                    Every PR Anneal opens follows a fixed structure: a
                    one-line summary, one before/after example, the eval delta
                    with significance, and a{" "}
                    <strong className="font-medium text-[#444440]">
                      &ldquo;do not merge if&rdquo;
                    </strong>{" "}
                    guard—a sentence describing the conditions under which this
                    change would be harmful. Nothing gets merged without human
                    review.
                  </p>
                </div>
              </div>
            </section>

            <hr className="my-14 border-[#E3E2DA]" />

            {/* SDK reference */}
            <section id="reference" aria-labelledby="reference-heading" className="mb-14 scroll-mt-24">
              <h2
                id="reference-heading"
                className="mb-8 text-2xl font-semibold tracking-tight text-[#111110]"
              >
                SDK reference
              </h2>

              <div className="space-y-10">
                <div id="trace-decorator" className="scroll-mt-24">
                  <h3 className="mb-1 font-mono text-sm font-semibold text-[#111110]">
                    @trace
                  </h3>
                  <p className="mb-4 text-sm leading-relaxed text-[#78776C]">
                    Decorator that wraps an async function and records a trace
                    for each invocation.
                  </p>
                  <div className="overflow-hidden rounded-lg border border-[#E3E2DA]">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-[#E3E2DA] bg-[#F2F1ED]">
                          <th className="px-4 py-2.5 text-left font-medium text-[#444440]">
                            Parameter
                          </th>
                          <th className="px-4 py-2.5 text-left font-medium text-[#444440]">
                            Type
                          </th>
                          <th className="px-4 py-2.5 text-left font-medium text-[#444440]">
                            Description
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E3E2DA]">
                        {[
                          ["agent_id", "str", "Stable identifier for this agent. Used for clustering and PR targeting."],
                          ["client", "AnnealClient", "SDK client instance. Defaults to environment variable config."],
                          ["outcome_fn", "Callable | None", "Optional function(result) → outcome. Infers from result if omitted."],
                          ["session_id_fn", "Callable | None", "Optional function(kwargs) → session_id. Auto-generated if omitted."],
                        ].map(([param, type, desc]) => (
                          <tr key={param as string} className="bg-white">
                            <td className="px-4 py-3 font-mono text-xs text-[#2450B0]">
                              {param}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs text-[#444440]">
                              {type}
                            </td>
                            <td className="px-4 py-3 text-xs text-[#78776C]">
                              {desc}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div id="schema" className="scroll-mt-24">
                  <h3 className="mb-3 text-base font-semibold text-[#111110]">
                    Trace schema
                  </h3>
                  <p className="mb-3 text-sm leading-relaxed text-[#78776C]">
                    The full trace JSON sent to{" "}
                    <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">
                      POST /ingest
                    </code>
                    :
                  </p>
                  <CodeBlock lang="json" code={TRACE_SCHEMA} />
                </div>
              </div>
            </section>

            {/* Feedback prompt */}
            <div className="rounded-lg border border-[#E3E2DA] bg-[#F2F1ED] px-6 py-5">
              <p className="text-sm font-medium text-[#111110]">
                Something missing?
              </p>
              <p className="mt-1 text-sm text-[#78776C]">
                These docs cover the v1 SDK. If your setup isn&rsquo;t covered,{" "}
                <a
                  href="mailto:docs@anneal.dev"
                  className="text-[#2450B0] underline underline-offset-2 hover:no-underline"
                >
                  email us
                </a>
                .
              </p>
            </div>
          </article>
        </div>
      </div>

      <MarketingFooter />
    </>
  );
}

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg border border-[#E3E2DA] bg-[#111110] px-5 py-4 font-mono text-xs leading-relaxed text-[#D4D3CE]">
      <code data-lang={lang}>{code}</code>
    </pre>
  );
}
