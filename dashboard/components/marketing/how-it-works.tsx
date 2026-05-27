const steps = [
  {
    n: "01",
    title: "Connect in ten lines",
    body: "The Anneal SDK wraps your LangGraph agent. One import, one decorator. Traces start flowing immediately—no schema changes, no infrastructure.",
    code: `from anneal import trace

@trace(agent_id="support-v2")
async def run_agent(input: str) -> str:
    ...`,
  },
  {
    n: "02",
    title: "Cluster the failures",
    body: "Each week, Anneal embeds your production traces and groups them into failure patterns. Not by keyword—by semantic meaning. You see what's actually breaking and how often.",
    code: null,
  },
  {
    n: "03",
    title: "Optimize against a holdout",
    body: "GEPA runs reflective optimization against the failure clusters. Every candidate is tested on a held-out eval set it never saw during generation. Anything that doesn't beat baseline is discarded.",
    code: null,
  },
  {
    n: "04",
    title: "One gated pull request",
    body: "If a candidate passes, Anneal opens a single GitHub PR: one-line summary, before/after example, eval delta with significance, and a 'do not merge if' guard. You review and merge. Or you don't.",
    code: null,
  },
] as const;

export function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-heading">
      <h2
        id="how-heading"
        className="mb-12 text-2xl font-semibold tracking-tight text-[#111110]"
      >
        How it works
      </h2>

      <ol className="space-y-12" role="list">
        {steps.map((step) => (
          <li key={step.n} className="grid gap-4 sm:grid-cols-[3rem_1fr]">
            <span
              className="font-mono text-sm font-medium text-[#B5B4AE]"
              aria-hidden="true"
            >
              {step.n}
            </span>
            <div>
              <h3 className="mb-2 text-base font-semibold text-[#111110]">
                {step.title}
              </h3>
              <p className="mb-4 text-sm leading-relaxed text-[#78776C]">
                {step.body}
              </p>
              {step.code && (
                <pre className="overflow-x-auto rounded-lg border border-[#E3E2DA] bg-[#EEECEA] px-4 py-3 font-mono text-xs leading-relaxed text-[#444440]">
                  <code>{step.code}</code>
                </pre>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
