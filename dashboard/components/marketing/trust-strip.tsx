const points = [
  {
    title: "Holdout separation",
    body: "The eval set used to gate each PR is never seen during optimization. Anneal cannot overfit to its own test.",
  },
  {
    title: "Calibrated judge",
    body: "LLM-as-judge scores are calibrated against a human-labeled seed set. Agreement rate is logged and surfaced on every run.",
  },
  {
    title: "You approve every PR",
    body: "Anneal opens pull requests. It does not merge them. Your agent's prompt never changes without a human reviewing a diff.",
  },
] as const;

export function TrustStrip() {
  return (
    <section aria-labelledby="trust-heading">
      <h2 id="trust-heading" className="sr-only">
        Safety and trust
      </h2>
      <dl className="grid gap-8 sm:grid-cols-3">
        {points.map((p) => (
          <div key={p.title} className="border-t border-[#E3E2DA] pt-6">
            <dt className="mb-2 text-sm font-semibold text-[#111110]">
              {p.title}
            </dt>
            <dd className="text-sm leading-relaxed text-[#78776C]">{p.body}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-8 text-xs text-[#B5B4AE]">
        Agent API keys are stored in your own Key Vault and never appear in any
        LLM context. Anneal reads traces; it does not touch your agent&rsquo;s
        production credentials.
      </p>
    </section>
  );
}
