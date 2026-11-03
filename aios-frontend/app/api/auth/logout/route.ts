import { NextResponse } from "next/server";
import { callService } from "@/lib/server/services";
import { clearSessionCookies, getSession } from "@/lib/server/session";

/** Revoke the session server-side (so the refresh token is dead everywhere), then clear the cookies. */
export async function POST() {
  try {
    const session = await getSession();
    if (session) {
      await callService("identity", `/api/v1/sessions/${encodeURIComponent(session.sessionId)}/revoke`, {
        method: "POST",
        body: { reason: "user_logout" },
      });
    }
  } catch {
    // Signing out must always succeed locally; a revoke failure leaves only a short-lived access token behind.
  }
  await clearSessionCookies();
  return NextResponse.json({ ok: true });
}
