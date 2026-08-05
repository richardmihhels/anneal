import { redirect } from "next/navigation";
import {
  authenticateCredentials,
  createDemoSession,
  demoLoginEnabled,
  getOptionalSession,
  setSessionCookie,
} from "@/lib/auth";

async function continueToDemoOrg() {
  "use server";

  if (!demoLoginEnabled()) redirect("/login?error=demo-disabled");
  await setSessionCookie(createDemoSession());
  redirect("/app");
}

async function signIn(formData: FormData) {
  "use server";

  const session = authenticateCredentials(
    String(formData.get("email") ?? ""),
    String(formData.get("password") ?? ""),
  );
  if (!session) redirect("/login?error=invalid-credentials");
  await setSessionCookie(session);
  redirect("/app");
}

interface LoginPageProps {
  searchParams: Promise<{ error?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const session = await getOptionalSession();
  if (session) redirect("/app");
  const { error } = await searchParams;
  const demo = demoLoginEnabled();

  return (
    <div className="flex min-h-[70vh] max-w-xl flex-col justify-center">
      <div className="mb-8">
        <p className="mb-3 font-mono text-sm text-zinc-500">anneal</p>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
          Sign in to your organization
        </h1>
        <p className="mt-3 text-sm leading-6 text-zinc-500">
          Sessions are signed, expire after 24 hours, and are scoped to one
          organization before dashboard data is requested.
        </p>
      </div>

      {error && (
        <p role="alert" className="mb-4 text-sm text-red-400">
          {error === "invalid-credentials"
            ? "The email or password is incorrect."
            : "Demo login is disabled in this environment."}
        </p>
      )}

      {demo ? (
        <form action={continueToDemoOrg}>
          <button
            type="submit"
            className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-white"
          >
            Continue to Prompt 7 Demo
          </button>
        </form>
      ) : (
        <form action={signIn} className="space-y-4">
          <label className="block text-sm text-zinc-400">
            Email
            <input
              name="email"
              type="email"
              autoComplete="username"
              required
              className="mt-1.5 block w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100 outline-none focus:border-zinc-500"
            />
          </label>
          <label className="block text-sm text-zinc-400">
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className="mt-1.5 block w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100 outline-none focus:border-zinc-500"
            />
          </label>
          <button
            type="submit"
            className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-white"
          >
            Sign in
          </button>
        </form>
      )}
    </div>
  );
}
