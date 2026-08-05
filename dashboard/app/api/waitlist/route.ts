import { NextResponse } from "next/server";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as { email?: unknown } | null;
  const email = typeof body?.email === "string" ? body.email.trim().toLowerCase() : "";
  if (!EMAIL_PATTERN.test(email)) {
    return NextResponse.json({ error: "invalid_email" }, { status: 400 });
  }

  const webhookUrl = process.env.ANNEAL_WAITLIST_WEBHOOK_URL;
  if (!webhookUrl) {
    if (process.env.ANNEAL_ENV === "production") {
      return NextResponse.json({ error: "waitlist_not_configured" }, { status: 503 });
    }
    return NextResponse.json({ accepted: true, demo: true });
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = process.env.ANNEAL_WAITLIST_WEBHOOK_TOKEN;
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(webhookUrl, {
    method: "POST",
    headers,
    body: JSON.stringify({ email, source: "anneal-marketing" }),
    cache: "no-store",
  });
  if (!response.ok) {
    return NextResponse.json({ error: "waitlist_unavailable" }, { status: 502 });
  }
  return NextResponse.json({ accepted: true });
}
