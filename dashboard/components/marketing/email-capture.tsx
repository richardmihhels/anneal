"use client";

import { useState } from "react";

type Status = "idle" | "success" | "error";

function isValidEmail(v: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
}

export function EmailCapture() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");

  if (status === "success") {
    return (
      <p className="text-sm text-[#78776C]">
        You&rsquo;re on the list. We&rsquo;ll reach out when beta opens.
      </p>
    );
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!isValidEmail(email)) {
      setStatus("error");
      return;
    }
    // Stub — no backend yet
    setStatus("success");
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Beta waitlist"
      noValidate
      className="flex flex-col gap-3 sm:flex-row sm:items-start"
    >
      <div className="flex flex-col gap-1.5">
        <input
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (status === "error") setStatus("idle");
          }}
          placeholder="you@company.com"
          aria-label="Work email"
          aria-invalid={status === "error"}
          aria-describedby={status === "error" ? "email-error" : undefined}
          autoComplete="email"
          className={[
            "h-10 w-full rounded-md border bg-white px-3 text-sm text-[#111110]",
            "placeholder:text-[#B5B4AE] focus:outline-none focus:ring-2 focus:ring-[#2450B0]/40",
            "sm:w-64",
            status === "error"
              ? "border-red-400"
              : "border-[#E3E2DA] focus:border-[#2450B0]",
          ]
            .filter(Boolean)
            .join(" ")}
        />
        {status === "error" && (
          <p id="email-error" role="alert" className="text-xs text-red-500">
            Enter a valid email address.
          </p>
        )}
      </div>
      <button
        type="submit"
        className={[
          "h-10 rounded-md bg-[#2450B0] px-4 text-sm font-medium text-white",
          "transition-colors hover:bg-[#1A3E9E]",
          "focus:outline-none focus:ring-2 focus:ring-[#2450B0]/40 focus:ring-offset-2 focus:ring-offset-[#F8F7F4]",
          "whitespace-nowrap",
        ].join(" ")}
      >
        Request access
      </button>
    </form>
  );
}
