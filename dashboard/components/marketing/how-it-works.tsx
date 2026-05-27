const steps = [
  {
    n: "01",
    title: "Connect",
    body: "The Anneal SDK wraps your LangGraph agent in roughly ten lines. Traces stream in immediately, with no schema changes and no new infrastructure.",
    code: `from anneal import trace

@trace(agent_id="support-v2")
async def run_agent(input: str) -> str:
    ...`,
  },
  {
    n: "02",
    title: "Watch",
    body: "The Health view shows eval score, failure categories, and open alarms every day. Quiet weeks still show whether the agent is holding steady.",
    code: null,
  },
  {
    n: "03",
    title: "Alarm",
    body: "If a failure category spikes above its recent baseline, Anneal sends a precise alarm within hours: what moved, how many conversations, and a cause hypothesis labeled as a guess.",
    code: null,
  },
  {
    n: "04",
    title: "Improve",
    body: "Once a week, Anneal clusters failures, runs GEPA/DSPy optimization against a held-out eval set, and opens one gated PR if it beats baseline. If nothing clears the holdout, no PR ships and the digest still tells you what was seen.",
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

      <div className="grid gap-px border border-[#E3E2DA] bg-[#E3E2DA] sm:grid-cols-2">
        {steps.map((step) => (
          <article
            key={step.n}
            className="bg-[#F8F7F4] p-7"
          >
            <span
              className="mb-4 block font-mono text-xs font-medium text-[#B5B4AE]"
              aria-hidden="true"
            >
              {step.n}
            </span>
            <h3 className="mb-2.5 text-base font-semibold text-[#111110]">
              {step.title}
            </h3>
            <p className="text-sm leading-relaxed text-[#78776C]">
              {step.body}
            </p>
            {step.code && (
              <pre className="mt-5 overflow-x-auto rounded-lg border border-[#E3E2DA] bg-white px-4 py-3.5 font-mono text-xs leading-relaxed text-[#444440]">
                <code>{step.code}</code>
              </pre>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
