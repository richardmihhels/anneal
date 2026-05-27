import { requireSession } from "@/lib/auth";

export default async function ConnectPage() {
  const session = await requireSession();

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-zinc-100">Connect</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Wire your agent into Anneal in three steps.
        </p>
      </div>

      <div className="space-y-4">
        <Step
          number={1}
          title="Install the Anneal SDK"
          status="done"
        >
          <p className="mb-3 text-sm text-zinc-400">
            Add the SDK to your agent&apos;s dependencies:
          </p>
          <pre className="rounded-lg bg-zinc-950 border border-zinc-800 px-4 py-3 font-mono text-sm text-zinc-300">
            pip install anneal-sdk[langchain]
          </pre>
          <p className="mt-3 text-sm text-zinc-400">
            Then attach the callback handler to your LangGraph run:
          </p>
          <pre className="mt-2 rounded-lg bg-zinc-950 border border-zinc-800 px-4 py-3 font-mono text-xs text-zinc-400 leading-relaxed">
{`from anneal_sdk import AnnealClient

anneal = AnnealClient.from_env()
handler = anneal.callback_handler(agent_id="cascade-support-v1")

result = graph.invoke(
    {"messages": messages},
    config={"callbacks": [handler]},
)
anneal.flush()`}
          </pre>
          <div className="mt-3 rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
            <p className="text-xs text-zinc-500">
              Use{" "}
              <code className="rounded bg-zinc-950 px-1 py-0.5 text-zinc-400">
                ANNEAL_ORG_ID={session.organizationId}
              </code>{" "}
              so traces land in {session.organizationName}.
            </p>
          </div>
        </Step>

        <Step
          number={2}
          title="Install the GitHub App"
          status="pending"
        >
          <p className="mb-4 text-sm text-zinc-400">
            Anneal needs write access to your repo to open PRs with prompt
            improvements.
          </p>
          <button
            disabled
            className="inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm text-zinc-400 cursor-not-allowed"
          >
            <GitHubIcon />
            Install on GitHub
            <span className="text-xs text-zinc-600">(coming soon)</span>
          </button>
          <div className="mt-3 rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
            <p className="text-xs text-zinc-500">
              The app requests:{" "}
              <span className="text-zinc-400">
                Contents (read/write), Pull requests (write)
              </span>
              . It never reads your agent code — only the config file you
              specify.
            </p>
          </div>
        </Step>

        <Step
          number={3}
          title="Configure your agent"
          status="pending"
        >
          <p className="mb-3 text-sm text-zinc-400">
            Add an <code className="rounded bg-zinc-800 px-1 py-0.5 text-xs text-zinc-300">anneal.yml</code> to your repo root:
          </p>
          <pre className="rounded-lg bg-zinc-950 border border-zinc-800 px-4 py-3 font-mono text-xs text-zinc-400 leading-relaxed">
{`organization_id: ${session.organizationId}
agent_id: cascade-support-v1
repo: acme/agent
config_path: agent/prompts.py
base_branch: main

# Provide 20+ labeled examples for the eval judge.
# Labels: "pass" | "fail"
seed_set:
  - context: "I've processed your refund of $79. It will arrive in 3–5 days."
    label: pass
  - context: "I cannot help with billing. Please contact billing@company.com."
    label: fail`}
          </pre>
          <p className="mt-3 text-xs text-zinc-500">
            Anneal runs every Monday at 02:00 UTC. Your first run will appear
            in{" "}
            <a href="/runs" className="text-zinc-400 hover:text-zinc-200 underline underline-offset-2 transition-colors">
              Runs
            </a>{" "}
            within the hour.
          </p>
        </Step>
      </div>
    </div>
  );
}

function Step({
  number,
  title,
  status,
  children,
}: {
  number: number;
  title: string;
  status: "done" | "pending";
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/30">
      <div className="flex items-center gap-3 border-b border-zinc-800 px-4 py-3">
        <div
          className={[
            "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
            status === "done"
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-zinc-800 text-zinc-500",
          ].join(" ")}
        >
          {status === "done" ? "✓" : number}
        </div>
        <h2 className="text-sm font-medium text-zinc-200">{title}</h2>
        {status === "done" && (
          <span className="ml-auto text-xs text-emerald-600">Installed</span>
        )}
      </div>
      <div className="px-4 py-4">{children}</div>
    </div>
  );
}

function GitHubIcon() {
  return (
    <svg
      viewBox="0 0 16 16"
      width="14"
      height="14"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}
