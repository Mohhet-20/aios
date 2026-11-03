import "server-only";
import { cookies } from "next/headers";
import { errors, jwtVerify } from "jose";
import { COOKIE, jwtSecret } from "./config";
import { callService, ServiceError } from "./services";

/** What the edge knows about the caller after verifying their access token. */
export interface Session {
  userId: string;
  sessionId: string;
  organizationId: string | null;
  email: string | null;
  displayName: string | null;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

const PROFILE_COOKIE = "aios_profile";
const secure = process.env.NODE_ENV === "production";

async function verify(token: string): Promise<{ sub: string; sid: string; org: string | null } | null> {
  try {
    const { payload } = await jwtVerify(token, jwtSecret(), { algorithms: ["HS256"] });
    if (typeof payload.sub !== "string" || typeof payload.sid !== "string") return null;
    return { sub: payload.sub, sid: payload.sid, org: typeof payload.org === "string" ? payload.org : null };
  } catch (err) {
    if (err instanceof errors.JWTExpired || err instanceof errors.JOSEError) return null;
    throw err;
  }
}

/** Store tokens in httpOnly cookies: never readable by page scripts, sent only to this origin. */
export async function writeSessionCookies(tokens: TokenPair, profile?: { email: string; display_name?: string | null }) {
  const jar = await cookies();
  const base = { httpOnly: true, secure, sameSite: "lax" as const, path: "/" };
  jar.set(COOKIE.access, tokens.access_token, { ...base, maxAge: 60 * 15 });
  jar.set(COOKIE.refresh, tokens.refresh_token, { ...base, maxAge: 60 * 60 * 24 * 30 });
  if (profile) {
    const value = Buffer.from(JSON.stringify({ email: profile.email, name: profile.display_name ?? null })).toString("base64url");
    jar.set(PROFILE_COOKIE, value, { ...base, maxAge: 60 * 60 * 24 * 30 });
  }
}

export async function clearSessionCookies() {
  const jar = await cookies();
  for (const name of [COOKIE.access, COOKIE.refresh, PROFILE_COOKIE]) jar.delete(name);
}

/**
 * The verified caller, or null. An expired access token is rotated once with the refresh token (the identity
 * service revokes and re-issues it), so a user stays signed in for the refresh token's lifetime.
 */
export async function getSession(): Promise<Session | null> {
  const jar = await cookies();
  let claims = jar.get(COOKIE.access)?.value ? await verify(jar.get(COOKIE.access)!.value) : null;

  if (!claims) {
    const refresh = jar.get(COOKIE.refresh)?.value;
    if (!refresh) return null;
    try {
      const rotated = await callService<TokenPair>("identity", "/api/v1/sessions/refresh", {
        method: "POST",
        body: { refresh_token: refresh },
      });
      claims = await verify(rotated.access_token);
      if (!claims) return null;
      await writeSessionCookies(rotated);
    } catch (err) {
      if (err instanceof ServiceError && err.status < 500) {
        await clearSessionCookies();
        return null;
      }
      throw err;
    }
  }

  let email: string | null = null;
  let displayName: string | null = null;
  const raw = jar.get(PROFILE_COOKIE)?.value;
  if (raw) {
    try {
      const parsed = JSON.parse(Buffer.from(raw, "base64url").toString("utf8")) as { email?: string; name?: string };
      email = parsed.email ?? null;
      displayName = parsed.name ?? null;
    } catch {
      /* a malformed profile cookie only costs the display name */
    }
  }
  return { userId: claims.sub, sessionId: claims.sid, organizationId: claims.org, email, displayName };
}
