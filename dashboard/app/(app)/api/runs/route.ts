import { NextResponse } from "next/server";
import { listRuns } from "@/lib/data";
import { getOptionalSession } from "@/lib/auth";

export async function GET() {
  const session = await getOptionalSession();
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  return NextResponse.json(await listRuns(session.organizationId));
}
