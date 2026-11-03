import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/server/route";
import { callService, ServiceError } from "@/lib/server/services";
import { writeSessionCookies } from "@/lib/server/session";

interface TokenResponse {
  user: { id: string; email: string; display_name: string | null };
  access_token: string;
  refresh_token: string;
}

/** Password (+ MFA code) sign-in. Tokens go into httpOnly cookies; the browser only learns who it is. */
export async function POST(req: Request) {
  let body: { email?: unknown; password?: unknown; mfa_code?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }
  if (typeof body.email !== "string" || typeof body.password !== "string" || !body.email || !body.password) {
    return NextResponse.json({ error: "invalid_request", detail: "email and password are required" }, { status: 400 });
  }
  try {
    const result = await callService<TokenResponse>("identity", "/api/v1/auth/token", {
      method: "POST",
      body: {
        email: body.email.trim(),
        password: body.password,
        mfa_code: typeof body.mfa_code === "string" && body.mfa_code ? body.mfa_code : undefined,
        user_agent: req.headers.get("user-agent") ?? undefined,
      },
    });
    await writeSessionCookies(result, result.user);
    return NextResponse.json({ user: { email: result.user.email, displayName: result.user.display_name } });
  } catch (err) {
    if (err instanceof ServiceError && (err.status === 401 || err.status === 403 || err.status === 423)) {
      if (err.type === "MfaRequiredError" || err.type === "InvalidMfaCodeError") {
        return NextResponse.json({ error: "mfa_required", detail: err.message }, { status: 401 });
      }
      if (err.type === "AccountLockedError") {
        return NextResponse.json({ error: "locked", detail: err.message }, { status: 423 });
      }
      // Wrong password, unknown email and unverified account all get one answer: no account enumeration.
      return NextResponse.json({ error: "invalid_credentials", detail: "Email or password is incorrect." }, { status: 401 });
    }
    return errorResponse(err);
  }
}
