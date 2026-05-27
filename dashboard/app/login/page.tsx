import { redirect } from "next/navigation";
import {
  createDemoSession,
  getOptionalSession,
  setSessionCookie,
} from "@/lib/auth";

async function continueToDemoOrg() {
  "use server";

  await setSessionCookie(createDemoSession());
  redirect("/");
}

export default async function LoginPage() {
  const session = await getOptionalSession();
  if (session) redirect("/");

  return (
    <div className="flex min-h-[70vh] max-w-xl flex-col justify-center">
      <div className="mb-8">
        <p className="mb-3 font-mono text-sm text-zinc-500">anneal</p>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
          Sign in to your organization
        </h1>
        <p className="mt-3 text-sm leading-6 text-zinc-500">
          V1 uses an Auth.js-style credentials session so the local smoke path
          works without a hosted identity provider. Data is scoped to the signed
          organization id before it reaches the dashboard.
        </p>
      </div>

      <form action={continueToDemoOrg}>
        <button
          type="submit"
          className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-white"
        >
          Continue to Prompt 7 Demo
        </button>
      </form>

      <p className="mt-4 text-xs leading-5 text-zinc-600">
        Production deployments should set{" "}
        <code className="rounded bg-zinc-900 px-1 py-0.5 text-zinc-400">
          AUTH_SECRET
        </code>{" "}
        and replace this credentials shim with the configured Auth.js provider.
      </p>
    </div>
  );
}
