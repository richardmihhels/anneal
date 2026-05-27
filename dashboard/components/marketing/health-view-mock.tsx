const categories = [
  { name: "Escalation", value: "2.1%", trend: "stable" },
  { name: "Refund policy", value: "1.4%", trend: "down" },
  { name: "Tool routing", value: "0.8%", trend: "stable" },
] as const;

export function HealthViewMock() {
  return (
    <figure
      aria-label="Agent Health view preview"
      className="overflow-hidden rounded-xl border border-[#E3E2DA] bg-white text-left shadow-sm"
    >
      <div className="border-b border-[#E3E2DA] px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-[#111110]">Agent Health</p>
            <p className="mt-1 font-mono text-xs text-[#B5B4AE]">
              cascade-support-v1 · last 8 weeks
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
            Stable
          </span>
        </div>
      </div>

      <div className="grid gap-px bg-[#E3E2DA] sm:grid-cols-[1.35fr_1fr]">
        <div className="bg-[#FAFAF8] px-5 py-5">
          <div className="mb-4 flex items-baseline justify-between">
            <div>
              <p className="font-mono text-[10px] font-medium uppercase tracking-widest text-[#B5B4AE]">
                eval score
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-[#111110]">
                91.8%
              </p>
            </div>
            <p className="text-xs text-emerald-700">+3.4 pts over 8 weeks</p>
          </div>

          <div
            className="relative h-32 rounded-lg border border-[#E3E2DA] bg-white px-3 py-3"
            role="img"
            aria-label="Eval score trend rising over time"
          >
            <div className="absolute inset-x-3 top-1/4 border-t border-[#EEECEA]" />
            <div className="absolute inset-x-3 top-1/2 border-t border-[#EEECEA]" />
            <div className="absolute inset-x-3 top-3/4 border-t border-[#EEECEA]" />
            {[
              { left: "8%", top: "70%", width: "14%", transform: "rotate(-8deg)" },
              { left: "21%", top: "67%", width: "14%", transform: "rotate(3deg)" },
              { left: "34%", top: "62%", width: "15%", transform: "rotate(-17deg)" },
              { left: "48%", top: "52%", width: "15%", transform: "rotate(-9deg)" },
              { left: "62%", top: "45%", width: "15%", transform: "rotate(-14deg)" },
              { left: "76%", top: "36%", width: "15%", transform: "rotate(-8deg)" },
            ].map((segment) => (
              <span
                key={`${segment.left}-${segment.transform}`}
                className="absolute h-0.5 origin-left rounded-full bg-[#2450B0]"
                style={segment}
                aria-hidden="true"
              />
            ))}
            <span
              className="absolute h-2 w-2 rounded-full bg-[#2450B0]"
              style={{ left: "76%", top: "34%" }}
              aria-hidden="true"
            />
            <div className="absolute bottom-4 right-4 rounded-full border border-[#E3E2DA] bg-white px-2 py-1 text-[10px] font-medium text-[#78776C]">
              alarm cleared
            </div>
          </div>
        </div>

        <div className="bg-white px-5 py-5">
          <p className="mb-4 font-mono text-[10px] font-medium uppercase tracking-widest text-[#B5B4AE]">
            failure categories
          </p>
          <div className="space-y-3">
            {categories.map((category) => (
              <div key={category.name}>
                <div className="mb-1.5 flex items-center justify-between gap-3">
                  <span className="text-xs font-medium text-[#444440]">
                    {category.name}
                  </span>
                  <span className="font-mono text-xs text-[#78776C]">
                    {category.value}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-[#EEECEA]">
                  <div
                    className={[
                      "h-full rounded-full",
                      category.trend === "down" ? "bg-emerald-500" : "bg-[#2450B0]",
                    ].join(" ")}
                    style={{ width: category.trend === "down" ? "38%" : "56%" }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
            <p className="text-xs font-medium text-emerald-800">
              Policy spike cleared
            </p>
            <p className="mt-1 text-xs leading-relaxed text-emerald-700">
              Back inside baseline after 14 affected conversations.
            </p>
          </div>
        </div>
      </div>
    </figure>
  );
}
