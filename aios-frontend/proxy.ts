import { NextResponse, type NextRequest } from "next/server";

/**
 * Sends signed-out visitors to /login. This is routing only: it checks that a session cookie exists, while every
 * /api/console route verifies the token itself, so a forged cookie gets a sign-in page's worth of nothing.
 */
export function proxy(req: NextRequest) {
  const hasSession = req.cookies.has("aios_at") || req.cookies.has("aios_rt");
  if (hasSession) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = req.nextUrl.pathname === "/" ? "" : `?next=${encodeURIComponent(req.nextUrl.pathname)}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Everything except the sign-in page, the edge API (it answers 401 itself) and static assets.
  matcher: ["/((?!login|api|_next/static|_next/image|favicon.ico|.*\\.(?:png|svg|jpg|ico|webp)$).*)"],
};
