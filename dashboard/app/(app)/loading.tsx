export default function AppLoading() {
  return (
    <div className="max-w-3xl animate-pulse space-y-4" aria-label="Loading dashboard">
      <div className="h-7 w-48 rounded bg-zinc-800" />
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="h-28 rounded-lg bg-zinc-900" />
        <div className="h-28 rounded-lg bg-zinc-900" />
        <div className="h-28 rounded-lg bg-zinc-900" />
      </div>
      <div className="h-72 rounded-lg bg-zinc-900" />
    </div>
  );
}
