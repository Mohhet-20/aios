import { NextResponse } from "next/server";
import { guestAccessEnabled } from "@/lib/server/config";
import { errorResponse } from "@/lib/server/route";
import { callService, ServiceError } from "@/lib/server/services";
import { writeSessionCookies } from "@/lib/server/session";

interface TokenResponse {
  user: { id: string; email: string; display_name: string | null };
  access_token: string;
  refresh_token: string;
}

/**
 * Hosted public demo: "Explore the live demo". The identity service opens a session for the configured guest account
 * (an ordinary member, never an owner or administrator) with no password involved; tokens go into the same httpOnly
 * cookies as a normal sign-in. Off unless AIOS_GUEST_ACCESS=true here and guest access is enabled in identity.
 */
export async function POST(req: Request) {
  if (!guestAccessEnabled()) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  try {
    const result = await callService<TokenResponse>("identity", "/api/v1/auth/guest", {
      method: "POST",
      body: { user_agent: req.headers.get("user-agent") ?? undefined },
    });
    await writeSessionCookies(result, result.user);
    return NextResponse.json({ user: { email: result.user.email, displayName: result.user.display_name } });
  } catch (err) {
    if (err instanceof ServiceError && (err.status === 403 || err.status === 404)) {
      return NextResponse.json({ error: "guest_unavailable", detail: "The live demo is not available right now." }, { status: 503 });
    }
    return errorResponse(err);
  }
}
