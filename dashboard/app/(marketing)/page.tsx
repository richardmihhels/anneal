import { AnimateIn } from "@/components/marketing/animate-in";
import { EmailCapture } from "@/components/marketing/email-capture";
import { HealthViewMock } from "@/components/marketing/health-view-mock";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { PRMock } from "@/components/marketing/pr-mock";
import { SilenceSection } from "@/components/marketing/silence-section";
import { TrustStrip } from "@/components/marketing/trust-strip";

export default function HomePage() {
  return (
    <>
      <MarketingNav />

      <main id="main-content">
        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <section
          aria-labelledby="hero-heading"
          className="relative overflow-hidden border-b border-[#E3E2DA]"
          style={{
            backgroundImage:
              "radial-gradient(circle, #D5D4CC 1px, transparent 1px)",
            backgroundSize: "22px 22px",
          }}
        >
          {/* Fade vignette so dot grid doesn't fight the text */}
          <div className="absolute inset-0 bg-gradient-to-b from-[#F8F7F4]/60 via-[#F8F7F4]/80 to-[#F8F7F4]" />

          <div className="relative mx-auto max-w-4xl px-5 pb-24 pt-40 text-center sm:pt-48">
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#E3E2DA] bg-white px-3 py-1 font-mono text-[11px] font-medium uppercase tracking-widest text-[#78776C]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#2450B0]" aria-hidden="true" />
              Private beta
            </p>

            <h1
              id="hero-heading"
              className="mb-6 text-[2.75rem] font-semibold leading-[1.08] tracking-[-0.03em] text-[#111110] sm:text-6xl lg:text-[5rem]"
            >
              Continuous assurance
              <br />
              for production agents.
              <br />
              <span className="text-[#78776C]">Never worse.</span>
            </h1>

            <p className="mx-auto mb-10 max-w-xl text-lg leading-relaxed text-[#78776C]">
              Anneal watches your agent every day, alarms you when a failure
              category regresses, and once a week opens one holdout-gated PR
              that makes it measurably better.
            </p>

            <div id="waitlist" className="flex justify-center">
              <EmailCapture />
            </div>

            {/* Proof tags */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
              {["GEPA · ICLR 2026", "Holdout-gated evals", "LangGraph native"].map(
                (tag) => (
                  <span key={tag} className="text-xs text-[#B5B4AE]">
                    {tag}
                  </span>
                ),
              )}
            </div>

            <div className="mx-auto mt-12 max-w-3xl">
              <HealthViewMock />
            </div>
          </div>
        </section>

        {/* ── PR Showcase ───────────────────────────────────────────────────── */}
        <section
          aria-labelledby="showcase-heading"
          className="border-b border-[#E3E2DA] bg-white px-5 py-20"
        >
          <div className="mx-auto max-w-xl">
            <p
              id="showcase-heading"
              className="mb-8 text-center font-mono text-xs font-medium uppercase tracking-widest text-[#B5B4AE]"
            >
              What the weekly improvement looks like
            </p>
            <PRMock />
            <p className="mt-5 text-center text-xs text-[#B5B4AE]">
              One PR per statistically significant improvement. Human reviews
              and merges. Anneal stays silent when nothing clears the gate.
            </p>
          </div>
        </section>

        {/* ── How it works ──────────────────────────────────────────────────── */}
        <AnimateIn>
          <section
            id="how-it-works"
            aria-labelledby="how-heading"
            className="border-b border-[#E3E2DA] px-5 py-20"
          >
            <div className="mx-auto max-w-5xl">
              <HowItWorks />
            </div>
          </section>
        </AnimateIn>

        {/* ── Silence ───────────────────────────────────────────────────────── */}
        <AnimateIn delay={60}>
          <section className="border-b border-[#E3E2DA] bg-white px-5 py-20">
            <div className="mx-auto max-w-5xl">
              <SilenceSection />
            </div>
          </section>
        </AnimateIn>

        {/* ── Trust ─────────────────────────────────────────────────────────── */}
        <AnimateIn delay={120}>
          <section className="px-5 py-20">
            <div className="mx-auto max-w-5xl">
              <TrustStrip />
            </div>
          </section>
        </AnimateIn>
      </main>

      <MarketingFooter />
    </>
  );
}
