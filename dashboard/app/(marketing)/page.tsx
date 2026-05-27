import { AnimateIn } from "@/components/marketing/animate-in";
import { EmailCapture } from "@/components/marketing/email-capture";
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

      <main id="main-content" className="mx-auto max-w-5xl px-5">
        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <section
          className="pb-20 pt-36 sm:pt-40"
          aria-labelledby="hero-heading"
        >
          <div className="grid gap-16 lg:grid-cols-[1fr_1.1fr] lg:items-start lg:gap-12">
            {/* Left: copy */}
            <div>
              <p className="mb-5 font-mono text-xs font-medium uppercase tracking-widest text-[#B5B4AE]">
                Private beta
              </p>

              <h1
                id="hero-heading"
                className="mb-6 text-[2.4rem] font-semibold leading-[1.12] tracking-tight text-[#111110] sm:text-5xl"
              >
                Your agent,
                <br />
                measurably better.
                <br />
                <span className="text-[#78776C]">Never worse.</span>
              </h1>

              <p className="mb-8 max-w-md text-base leading-relaxed text-[#78776C]">
                Anneal ingests your production traces, clusters failures, runs
                statistically gated prompt optimization, and opens one GitHub PR
                a week. Dependabot for your agent&rsquo;s prompts and skills.
              </p>

              <div id="waitlist" className="mb-8">
                <EmailCapture />
              </div>

              <p className="text-xs text-[#B5B4AE]">
                Built on GEPA — reflective optimization, ICLR 2026.
              </p>
            </div>

            {/* Right: PR mock */}
            <div className="lg:pt-2">
              <PRMock />
            </div>
          </div>
        </section>

        {/* ── How it works ─────────────────────────────────────────────────── */}
        <AnimateIn className="mb-20">
          <HowItWorks />
        </AnimateIn>

        {/* ── Silence ──────────────────────────────────────────────────────── */}
        <AnimateIn delay={60} className="mb-20">
          <SilenceSection />
        </AnimateIn>

        {/* ── Trust strip ──────────────────────────────────────────────────── */}
        <AnimateIn delay={120} className="mb-24">
          <TrustStrip />
        </AnimateIn>
      </main>

      <MarketingFooter />
    </>
  );
}
