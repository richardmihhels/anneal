import { RunsTimeline } from "@/components/runs-timeline";
import { listRunDetails } from "@/lib/data";
import { requireSession } from "@/lib/auth";

export default async function RunsPage() {
  const session = await requireSession();
  const runs = listRunDetails(session.organizationId);
  const shipped = runs.reduce((sum, run) => sum + run.gate.prs_opened, 0);
  const held = runs.reduce((sum, run) => sum + run.gate.rejected, 0);

  return (
    <div className="max-w-5xl">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Runs</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {runs.length} weekly optimization cycles from Prompt 7 synthetic
            run records for {session.organizationName}.
          </p>
        </div>
        <div className="flex gap-4 text-right text-xs">
          <div>
            <p className="font-mono text-lg text-emerald-400">{shipped}</p>
            <p className="text-zinc-600">PRs shipped</p>
          </div>
          <div>
            <p className="font-mono text-lg text-zinc-300">{held}</p>
            <p className="text-zinc-600">held by gate</p>
          </div>
        </div>
      </div>

      <RunsTimeline runs={runs} />
    </div>
  );
}
