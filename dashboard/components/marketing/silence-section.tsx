export function SilenceSection() {
  return (
    <section aria-labelledby="silence-heading" className="max-w-3xl">
      <p className="mb-4 font-mono text-xs font-medium uppercase tracking-widest text-[#B5B4AE]">
        Philosophy
      </p>
      <h2
        id="silence-heading"
        className="mb-6 text-3xl font-semibold tracking-tight text-[#111110] sm:text-4xl"
      >
        Silence is a feature,
        <br />
        not a gap.
      </h2>
      <div className="space-y-4 text-base leading-relaxed text-[#78776C]">
        <p>
          Most optimization tools ship something every cycle. Anneal
          doesn&rsquo;t. If no candidate passes the eval gate this week—if every
          mutation either regresses on the holdout or fails to reach
          statistical significance—Anneal opens no PR and sends no
          notification.
        </p>
        <p>
          The cost of a false positive in prompt engineering is a production
          regression that erodes user trust and takes weeks to diagnose. The
          cost of a false negative is missing one week of improvement.
          We&rsquo;ve made that tradeoff explicitly, every time.
        </p>
        <p className="font-medium text-[#444440]">
          Less optimization that is always net-positive beats more optimization
          that overfits. Goodhart&rsquo;s Law is the primary risk—not a
          footnote.
        </p>
      </div>
    </section>
  );
}
