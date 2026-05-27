import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-t border-[#E3E2DA]">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-5 py-10 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <span className="font-mono text-sm font-semibold text-[#111110]">
            anneal
          </span>
          <p className="mt-1 text-xs text-[#B5B4AE]">
            Anneal — Tartu, Estonia.
          </p>
        </div>

        <nav aria-label="Footer navigation">
          <ul className="flex flex-wrap gap-x-6 gap-y-2" role="list">
            <li>
              <Link
                href="/docs"
                className="text-xs text-[#78776C] transition-colors hover:text-[#111110] focus:outline-none focus:underline"
              >
                Docs
              </Link>
            </li>
            <li>
              <Link
                href="/privacy"
                className="text-xs text-[#78776C] transition-colors hover:text-[#111110] focus:outline-none focus:underline"
              >
                Privacy
              </Link>
            </li>
            <li>
              <Link
                href="/terms"
                className="text-xs text-[#78776C] transition-colors hover:text-[#111110] focus:outline-none focus:underline"
              >
                Terms
              </Link>
            </li>
            <li>
              <a
                href="https://github.com/annealhq"
                className="text-xs text-[#78776C] transition-colors hover:text-[#111110] focus:outline-none focus:underline"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
