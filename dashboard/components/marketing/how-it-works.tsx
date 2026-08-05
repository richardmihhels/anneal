const steps = [
  {
    n: "01",
    title: "Connect",
    body: "Attach the Anneal callback to an existing LangGraph invocation. The client scrubs likely secrets and sends LangSmith-shaped runs in a background queue.",
    code: `from anneal_sdk import AnnealClient

anneal = AnnealClient.from_env()
handler = anneal.callback_handler("support-v2")`,
  },
  {
    n: "02",
    title: "Watch",
    body: "The Health view shows recorded eval scores, failure categories, and open alarms. Quiet weeks still show whether the agent held steady.",
    code: null,
  },
  {
    n: "03",
    title: "Detect",
    body: "The regression detector compares rolling windows with a one-sided proportions test, debounces repeats, and labels its cause hypothesis as a guess.",
    code: null,
  },
  {
    n: "04",
    title: "Improve",
    body: "Once a week, Anneal clusters only the training split, evaluates candidates on a reserved holdout, and opens the strongest gated PR. If nothing clears the holdout, no PR ships and the digest records the safe outcome.",
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
