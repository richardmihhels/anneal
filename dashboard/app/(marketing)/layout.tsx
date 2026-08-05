import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Anneal — Your agent, measurably better. Never worse.",
  description:
    "Anneal ingests production traces, clusters failures, runs statistically gated optimization, and opens one GitHub PR a week. Dependabot for AI agent prompts.",
  openGraph: {
    title: "Anneal — Your agent, measurably better. Never worse.",
    description:
      "Weekly prompt optimization for production LangGraph agents. Holdout-gated, LLM-as-judge calibrated. Refuses to ship regressions.",
    type: "website",
  },
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className="min-h-screen bg-[#F8F7F4] font-sans text-[#111110] antialiased"
      style={{ colorScheme: "light" }}
    >
      {/* 2px accent bar */}
      <div className="fixed inset-x-0 top-0 z-50 h-0.5 bg-[#2450B0]" aria-hidden="true" />

      {/* Skip to content */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-[#2450B0] focus:px-3 focus:py-1.5 focus:text-sm focus:text-white"
      >
        Skip to content
      </a>

      <style>{`
        @media (prefers-reduced-motion: no-preference) {
          [data-animate] {
            opacity: 0;
            transform: translateY(20px);
            transition:
              opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
          }
          [data-animate][data-visible="true"] {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>

      {children}
    </div>
  );
}
