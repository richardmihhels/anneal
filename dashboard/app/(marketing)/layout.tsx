import type { Metadata } from "next";
import { DM_Sans } from "next/font/google";

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

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-dm-sans",
  display: "swap",
});

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className={`${dmSans.variable} min-h-screen bg-[#F8F7F4] font-[family-name:var(--font-dm-sans)] text-[#111110] antialiased`}
      style={{ colorScheme: "light" }}
    >
      <style>{`
        @media (prefers-reduced-motion: no-preference) {
          [data-animate] {
            opacity: 0;
            transform: translateY(18px);
            transition:
              opacity 0.55s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.55s cubic-bezier(0.16, 1, 0.3, 1);
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
