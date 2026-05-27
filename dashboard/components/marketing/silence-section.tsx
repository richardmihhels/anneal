export function SilenceSection() {
  return (
    <section
      aria-labelledby="silence-heading"
      className="rounded-xl border border-[#E3E2DA] bg-[#F2F1ED] px-8 py-10"
    >
      <h2
        id="silence-heading"
        className="mb-4 text-xl font-semibold tracking-tight text-[#111110]"
      >
        Silence is a feature.
      </h2>
      <div className="max-w-prose space-y-4 text-sm leading-relaxed text-[#78776C]">
        <p>
          Most optimization tools ship something every cycle. Anneal doesn&rsquo;t.
          If no candidate passes the eval gate this week—if every mutation either
          regresses on the holdout or fails to reach significance—Anneal opens no
          PR and sends no notification.
        </p>
        <p>
          This is deliberate. The cost of a false positive in prompt engineering
          is a production regression that erodes user trust and takes weeks to
          diagnose. The cost of a false negative is missing one week of
          improvement. We&rsquo;ve chosen the second risk every time.
        </p>
        <p className="font-medium text-[#444440]">
          Less optimization that is always net-positive beats more optimization
          that overfits. Goodhart&rsquo;s Law is the primary risk here, not a
          footnote.
        </p>
      </div>
    </section>
  );
}
