import Link from "next/link";
import { notFound } from "next/navigation";
import { requireSession } from "@/lib/auth";
import { getWeeklyDigest } from "@/lib/data";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function DigestPage({ params }: PageProps) {
  const session = await requireSession();
  const { id } = await params;
  const digest = getWeeklyDigest(id, session.organizationId);
  if (!digest) notFound();

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <Link
          href="/runs"
          className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          ← Runs
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold text-zinc-100">Weekly digest</h1>
          <span
            className={[
              "rounded-full border px-2.5 py-0.5 text-xs font-medium",
              digest.pr_shipped
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                : "border-zinc-700 bg-zinc-900/70 text-zinc-400",
            ].join(" ")}
          >
            {digest.pr_shipped ? "PR shipped" : "No PR shipped"}
          </span>
        </div>
        <p className="mt-1 text-sm text-zinc-500">
          {digest.agent_id} · {formatDate(digest.week_start)} to{" "}
          {formatDate(digest.week_end)}
        </p>
      </div>

      <section className="mb-6 rounded-lg border border-zinc-800 bg-zinc-900/30 px-5 py-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
          Summary
        </p>
        <p className="text-sm leading-relaxed text-zinc-300">{digest.summary}</p>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-950 px-5 py-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500">
          Shareable digest
        </p>
        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-300">
          {digest.page_body}
        </pre>
      </section>
    </div>
  );
}
