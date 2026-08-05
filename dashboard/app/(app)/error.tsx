"use client";

import { useEffect } from "react";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="max-w-xl rounded-lg border border-red-500/20 bg-red-500/5 p-6">
      <h1 className="text-lg font-semibold text-zinc-100">Dashboard data is unavailable</h1>
      <p className="mt-2 text-sm leading-6 text-zinc-400">
        Anneal could not load the organization snapshot. Check the API health,
        organization id, and server-side API key, then try again.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-5 rounded-md bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-950 hover:bg-white"
      >
        Try again
      </button>
    </div>
  );
}
