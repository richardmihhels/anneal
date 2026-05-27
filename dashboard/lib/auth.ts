import { createHmac, timingSafeEqual } from "crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const AUTH_COOKIE = "anneal_session";
export const DEMO_ORG_ID = "org_demo";
export const DEMO_ORG_NAME = "Prompt 7 Demo";
export const DEMO_USER_EMAIL = "lead@prompt7.example";

export interface AuthSession {
  userId: string;
  email: string;
  organizationId: string;
  organizationName: string;
}

export function createDemoSession(): AuthSession {
  return {
    userId: "user_demo_lead",
    email: DEMO_USER_EMAIL,
    organizationId: DEMO_ORG_ID,
    organizationName: DEMO_ORG_NAME,
  };
}

function authSecret(): string {
  const secret = process.env.AUTH_SECRET ?? process.env.ANNEAL_AUTH_SECRET;
  if (secret) return secret;
  if (process.env.NODE_ENV === "production") {
    throw new Error("AUTH_SECRET or ANNEAL_AUTH_SECRET is required in production");
  }
  return "anneal-local-dev-secret";
}

function sign(payload: string): string {
  return createHmac("sha256", authSecret()).update(payload).digest("base64url");
}

function encodePayload(session: AuthSession): string {
  return Buffer.from(JSON.stringify(session), "utf8").toString("base64url");
}

function decodePayload(payload: string): AuthSession | null {
  try {
    const raw = Buffer.from(payload, "base64url").toString("utf8");
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (
      typeof parsed.userId !== "string" ||
      typeof parsed.email !== "string" ||
      typeof parsed.organizationId !== "string" ||
      typeof parsed.organizationName !== "string"
    ) {
      return null;
    }
    return {
      userId: parsed.userId,
      email: parsed.email,
      organizationId: parsed.organizationId,
      organizationName: parsed.organizationName,
    };
  } catch {
    return null;
  }
}

function encodeSession(session: AuthSession): string {
  const payload = encodePayload(session);
  return `${payload}.${sign(payload)}`;
}

function decodeSession(raw: string | undefined): AuthSession | null {
  if (!raw) return null;
  const [payload, signature] = raw.split(".");
  if (!payload || !signature) return null;
  const expected = sign(payload);
  const actualBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);
  if (
    actualBuffer.length !== expectedBuffer.length ||
    !timingSafeEqual(actualBuffer, expectedBuffer)
  ) {
    return null;
  }
  return decodePayload(payload);
}

export async function getOptionalSession(): Promise<AuthSession | null> {
  const cookieStore = await cookies();
  return decodeSession(cookieStore.get(AUTH_COOKIE)?.value);
}

export async function requireSession(): Promise<AuthSession> {
  const session = await getOptionalSession();
  if (!session) redirect("/login");
  return session;
}

export async function setSessionCookie(session: AuthSession): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(AUTH_COOKIE, encodeSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
}

export async function clearSessionCookie(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(AUTH_COOKIE);
}
