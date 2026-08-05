import type { Metadata } from "next";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";

export const metadata: Metadata = {
  title: "Docs — Anneal",
  description: "Anneal SDK reference, deployment modes, and safety model.",
};

const SDK_INSTALL = `pip install "anneal-sdk[langchain] @ git+https://github.com/richardmihhels/anneal.git@main#subdirectory=sdk"`;

const SDK_QUICKSTART = `from anneal_sdk import AnnealClient

anneal = AnnealClient.from_env()
handler = anneal.callback_handler(agent_id="support-agent-v1")

result = graph.invoke(
    {"messages": messages},
    config={"callbacks": [handler]},
)

# Drain queued traces before a short-lived process exits.
anneal.flush()`;

const SDK_ENV = `export ANNEAL_ENDPOINT=http://localhost:8000
export ANNEAL_ORG_ID=org_demo
export ANNEAL_API_KEY=dev_optional`;

const OTEL_EXAMPLE = `curl -X POST "$ANNEAL_ENDPOINT/ingest/otel" \\
  -H "Authorization: Bearer $ANNEAL_API_KEY" \\
  -H "X-Anneal-Org: $ANNEAL_ORG_ID" \\
  -H "Content-Type: application/json" \\
  --data-binary @otlp-export.json`;

const TRACE_SCHEMA = `{
  "id": "trace-id",
  "organization_id": "org_acme",
  "agent_id": "support-agent-v1",
  "session_id": "conversation-id",
  "created_at": "2026-08-04T09:00:00Z",
  "spans": [
    {
      "id": "span-id",
      "trace_id": "trace-id",
      "name": "tool:lookup_order",
      "start_time": "2026-08-04T09:00:00Z",
      "end_time": "2026-08-04T09:00:00.342Z",
      "duration_ms": 342,
      "input": {},
      "output": {},
      "error": null,
      "metadata": {}
    }
  ],
  "outcome": "success",
  "metadata": {}
}`;

const TOC = [
  ["quickstart", "Quick start"],
  ["ingestion", "Ingestion"],
  ["concepts", "Core concepts"],
  ["safety", "Safety gate"],
  ["configuration", "Worker configuration"],
  ["reference", "SDK reference"],
] as const;

export default function DocsPage() {
  return (
    <>
      <MarketingNav />
      <main id="main-content" className="mx-auto max-w-5xl px-5 pb-24 pt-28">
        <div className="lg:grid lg:grid-cols-[220px_1fr] lg:gap-12">
          <aside className="hidden lg:block">
            <nav aria-label="Documentation navigation" className="sticky top-24">
              <p className="mb-3 font-mono text-[10px] font-medium uppercase tracking-widest text-[#B5B4AE]">
                On this page
              </p>
              <ul className="space-y-0.5">
                {TOC.map(([id, title]) => (
                  <li key={id}>
                    <a className="block rounded py-1 pl-2 text-sm text-[#78776C] hover:text-[#111110]" href={`#${id}`}>
                      {title}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>

          <article className="min-w-0">
            <header className="mb-12 border-b border-[#E3E2DA] pb-10">
              <p className="mb-3 font-mono text-xs font-medium uppercase tracking-widest text-[#B5B4AE]">
                Documentation
              </p>
              <h1 className="mb-4 text-3xl font-semibold tracking-tight text-[#111110] sm:text-4xl">
                Getting started
              </h1>
              <p className="text-base leading-relaxed text-[#78776C]">
                Anneal is a self-hosted beta for LangGraph and LangChain agents.
                It accepts scrubbed traces, clusters recurring failures from a
                training split, and evaluates focused prompt changes on a
                separate holdout before it can open one GitHub pull request.
              </p>
            </header>

            <DocSection id="quickstart" title="Quick start">
              <ol className="space-y-8">
                <li>
                  <h3 className="mb-3 font-semibold text-[#111110]">1. Install the SDK</h3>
                  <p className="mb-3 text-sm leading-relaxed text-[#78776C]">
                    Until the first tagged PyPI release, install directly from this repository.
                  </p>
                  <CodeBlock lang="bash" code={SDK_INSTALL} />
                </li>
                <li>
                  <h3 className="mb-3 font-semibold text-[#111110]">2. Configure the client</h3>
                  <CodeBlock lang="bash" code={SDK_ENV} />
                </li>
                <li>
                  <h3 className="mb-3 font-semibold text-[#111110]">3. Attach the callback</h3>
                  <p className="mb-3 text-sm leading-relaxed text-[#78776C]">
                    The callback implements the LangChain protocol by duck typing,
                    so the SDK does not add LangChain as a runtime requirement.
                  </p>
                  <CodeBlock lang="python" code={SDK_QUICKSTART} />
                </li>
              </ol>
            </DocSection>

            <DocSection id="ingestion" title="Ingestion">
              <p className="mb-4 text-sm leading-relaxed text-[#78776C]">
                The callback sends LangSmith-shaped runs to <InlineCode>/ingest/langsmith</InlineCode>.
                Existing OpenTelemetry collectors can instead post an OTLP JSON
                export directly to <InlineCode>/ingest/otel</InlineCode>; Anneal
                does not currently ship a custom OpenTelemetry exporter.
              </p>
              <CodeBlock lang="bash" code={OTEL_EXAMPLE} />
              <p className="mt-4 text-sm leading-relaxed text-[#78776C]">
                Production requests require a bearer key and organization header.
                The authenticated organization always overrides trace metadata,
                and likely credential fields are scrubbed before persistence.
              </p>
            </DocSection>

            <DocSection id="concepts" title="Core concepts">
              <div className="space-y-7 text-sm leading-relaxed text-[#78776C]">
                <Concept title="Trace and span">
                  A trace is one agent run or conversation. Spans are its nested
                  chain, model, and tool operations. Postgres stores replayable
                  trace payloads and product metadata; ClickHouse stores spans.
                </Concept>
                <Concept title="Failure cluster">
                  Anneal identifies failures, embeds their compact interaction
                  context, discards HDBSCAN noise, and labels only repeated groups.
                </Concept>
                <Concept title="Silent week">
                  Too little data, no stable cluster, weak judge calibration, a
                  non-significant delta, or an existing equivalent PR all result
                  in no new pull request. That is a successful safe outcome.
                </Concept>
              </div>
            </DocSection>

            <DocSection id="safety" title="Safety gate">
              <div className="space-y-4 text-sm leading-relaxed text-[#78776C]">
                <p>
                  Anneal deterministically reserves 20% of traces before
                  clustering. Clustering and mutation see only training traces;
                  the baseline and candidate are replayed on the same holdout cases.
                </p>
                <p>
                  A candidate must improve the paired mean and pass a one-sided
                  paired t-test at <InlineCode>p &lt; 0.05</InlineCode>. The LLM
                  judge is calibrated against human-labeled pass/fail examples and
                  must reach at least 75% agreement. The publisher independently
                  rechecks the gate and selects only the strongest surviving change.
                </p>
                <p>
                  Anneal opens a PR; it never merges one. The PR includes the
                  before/after prompt, holdout statistics, a representative failure,
                  and a do-not-merge guard for human review.
                </p>
              </div>
            </DocSection>

            <DocSection id="configuration" title="Worker configuration">
              <p className="mb-4 text-sm leading-relaxed text-[#78776C]">
                Copy <InlineCode>anneal.example.yml</InlineCode> and provide the
                organization, agent, GitHub repository, prompt file, baseline
                prompt, and at least four calibration examples containing both
                pass and fail labels. Unknown fields are rejected.
              </p>
              <p className="text-sm leading-relaxed text-[#78776C]">
                Production also requires Postgres, OpenAI embeddings, Anthropic
                judge/mutation credentials, a GitHub App installation, and a
                customer-owned replay endpoint. The replay endpoint receives a
                scrubbed trace plus candidate prompt and must return
                <InlineCode>{'{"response":"..."}'}</InlineCode>.
              </p>
            </DocSection>

            <DocSection id="reference" title="SDK reference">
              <div className="overflow-hidden rounded-lg border border-[#E3E2DA]">
                <table className="w-full text-sm">
                  <thead className="border-b border-[#E3E2DA] bg-[#F2F1ED] text-left text-[#444440]">
                    <tr><th className="px-4 py-2.5">API</th><th className="px-4 py-2.5">Purpose</th></tr>
                  </thead>
                  <tbody className="divide-y divide-[#E3E2DA] bg-white text-xs text-[#78776C]">
                    <RefRow api="AnnealClient(endpoint, api_key, organization_id=...)" purpose="Start a thread-safe client with a bounded background queue." />
                    <RefRow api="AnnealClient.from_env()" purpose="Read ANNEAL_ENDPOINT, ANNEAL_API_KEY, and ANNEAL_ORG_ID." />
                    <RefRow api="callback_handler(agent_id)" purpose="Create a LangChain/LangGraph callback handler for one stable agent ID." />
                    <RefRow api="flush()" purpose="Wait until queued trace deliveries have been attempted." />
                    <RefRow api="close()" purpose="Drain the queue and stop the worker thread." />
                  </tbody>
                </table>
              </div>
              <h3 className="mb-3 mt-8 font-semibold text-[#111110]">Normalized trace schema</h3>
              <CodeBlock lang="json" code={TRACE_SCHEMA} />
              <p className="mt-3 text-xs leading-relaxed text-[#78776C]">
                Outcome values are <InlineCode>success</InlineCode>, <InlineCode>failure</InlineCode>, or <InlineCode>unknown</InlineCode>.
              </p>
            </DocSection>

            <div className="rounded-lg border border-[#E3E2DA] bg-[#F2F1ED] px-6 py-5 text-sm text-[#78776C]">
              The repository also includes local demo, production deployment,
              SDK, security, and safety documentation alongside the source.
            </div>
          </article>
        </div>
      </main>
      <MarketingFooter />
    </>
  );
}

function DocSection({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mb-14 scroll-mt-24 border-b border-[#E3E2DA] pb-14">
      <h2 className="mb-6 text-xl font-semibold tracking-tight text-[#111110]">{title}</h2>
      {children}
    </section>
  );
}

function Concept({ title, children }: { title: string; children: React.ReactNode }) {
  return <p><strong className="font-medium text-[#444440]">{title}.</strong>{" "}{children}</p>;
}

function RefRow({ api, purpose }: { api: string; purpose: string }) {
  return <tr><td className="px-4 py-3 font-mono text-[#2450B0]">{api}</td><td className="px-4 py-3">{purpose}</td></tr>;
}

function InlineCode({ children }: { children: React.ReactNode }) {
  return <code className="rounded bg-[#EEECEA] px-1.5 py-0.5 font-mono text-xs text-[#444440]">{children}</code>;
}

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg border border-[#E3E2DA] bg-[#111110] px-5 py-4 font-mono text-xs leading-relaxed text-[#D4D3CE]">
      <code data-lang={lang}>{code}</code>
    </pre>
  );
}
