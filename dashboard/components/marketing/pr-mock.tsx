export function PRMock() {
  return (
    <figure
      aria-label="Example Anneal pull request"
      className="overflow-hidden rounded-xl border border-[#E3E2DA] bg-white shadow-sm"
    >
      {/* PR header */}
      <div className="border-b border-[#E3E2DA] px-5 py-4">
        <div className="mb-2 flex items-center gap-2.5">
          <span
            className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700"
            aria-label="Pull request status: Open"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
            Open
          </span>
          <span className="font-mono text-xs text-[#B5B4AE]">#47</span>
        </div>
        <p className="text-sm font-medium leading-snug text-[#111110]">
          feat(prompt): tighten escalation threshold in billing dispute handler
        </p>
        <p className="mt-1 font-mono text-xs text-[#B5B4AE]">
          anneal[bot] opened this · base: main
        </p>
      </div>

      {/* Diff */}
      <div className="border-b border-[#E3E2DA] bg-[#FAFAF8] px-5 py-4 font-mono text-xs">
        <p className="mb-2 text-[10px] font-medium uppercase tracking-widest text-[#B5B4AE]">
          prompt diff
        </p>
        <div className="space-y-2">
          <div className="flex gap-2">
            <span className="shrink-0 select-none text-red-400" aria-hidden="true">−</span>
            <span className="text-[#78776C] line-through">
              &ldquo;I&rsquo;ll transfer you to our billing team—they&rsquo;ll be able to
              assist.&rdquo;
            </span>
          </div>
          <div className="flex gap-2">
            <span className="shrink-0 select-none text-emerald-500" aria-hidden="true">+</span>
            <span className="text-[#111110]">
              &ldquo;I&rsquo;ve reviewed your account. The $47 charge from March 3rd was
              applied incorrectly—I&rsquo;m reversing it now.&rdquo;
            </span>
          </div>
        </div>
      </div>

      {/* Eval delta */}
      <div className="border-b border-[#E3E2DA] px-5 py-4">
        <div className="mb-3 flex items-baseline gap-3">
          <span className="text-2xl font-semibold tabular-nums text-emerald-600">
            +6.2%
          </span>
          <span className="text-xs text-[#78776C]">holdout eval delta</span>
        </div>
        <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-[#EEECEA]">
          <div
            className="h-full rounded-full bg-emerald-500"
            style={{ width: "62%" }}
            role="presentation"
          />
        </div>
        <p className="text-xs text-[#B5B4AE]">
          40 holdout cases &nbsp;·&nbsp; p&nbsp;=&nbsp;0.003 &nbsp;·&nbsp;
          <span className="text-[#78776C]">statistically significant</span>
        </p>
      </div>

      {/* Do-not-merge guard */}
      <div className="px-5 py-3.5 text-xs text-[#78776C]">
        <span className="font-medium text-[#111110]">Do not merge if</span>
        {" "}your billing escalation rate is below 2%—this change increases
        direct resolution attempts.
      </div>
    </figure>
  );
}
