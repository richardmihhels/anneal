/** @jest-environment node */

import { GET } from "@/app/health/route";

describe("dashboard health route", () => {
  it("returns an ok status", async () => {
    const response = GET();
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ status: "ok" });
  });
});
