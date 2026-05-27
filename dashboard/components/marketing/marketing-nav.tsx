export function MarketingNav() {
  return (
    <header className="fixed inset-x-0 top-0.5 z-20 border-b border-[#E3E2DA] bg-[#F8F7F4]/90 backdrop-blur-sm">
      <nav
        className="mx-auto flex h-13 max-w-5xl items-center justify-between px-5"
        aria-label="Main navigation"
        style={{ height: "52px" }}
      >
        <a
          href="/"
          className="font-mono text-sm font-semibold tracking-tight text-[#111110] focus:outline-none focus:underline"
        >
          anneal
        </a>

        <ul className="hidden items-center gap-6 sm:flex" role="list">
          <li>
            <a
              href="#how-it-works"
              className="text-sm text-[#78776C] transition-colors hover:text-[#111110] focus:outline-none focus:underline"
            >
              How it works
            </a>
          </li>
          <li>
            <a
              href="/docs"
              className="text-sm text-[#78776C] transition-colors hover:text-[#111110] focus:outline-none focus:underline"
            >
              Docs
            </a>
          </li>
        </ul>

        <a
          href="#waitlist"
          className="rounded-md bg-[#2450B0] px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1A3E9E] focus:outline-none focus:ring-2 focus:ring-[#2450B0]/40 focus:ring-offset-2 focus:ring-offset-[#F8F7F4]"
        >
          Request access
        </a>
      </nav>
    </header>
  );
}
