"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/runs", label: "Runs" },
  { href: "/connect", label: "Connect" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="fixed left-0 top-0 z-10 flex h-14 w-full items-center border-b border-zinc-800 bg-zinc-950 px-3 md:h-full md:w-52 md:flex-col md:items-stretch md:border-b-0 md:border-r md:py-5">
      <div className="mr-4 px-2 md:mb-6 md:mr-0">
        <span className="font-mono text-sm font-semibold tracking-tight text-zinc-100">
          anneal
        </span>
      </div>

      <ul className="flex gap-0.5 md:flex-col">
        {links.map(({ href, label }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                className={[
                  "block rounded px-2 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-zinc-800 text-zinc-50 font-medium"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200",
                ].join(" ")}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="ml-auto hidden px-2 md:ml-0 md:mt-auto md:block">
        <p className="text-xs text-zinc-600">cascade-support-v1</p>
      </div>
    </nav>
  );
}
