import "server-only";
import { NextResponse } from "next/server";
import { ServiceError } from "./services";
import { getSession, type Session } from "./session";

/** Wrap a console route: verified session required; service failures become JSON errors with the right status. */
export function withSession<C>(handler: (session: Session, req: Request, ctx: C) => Promise<unknown>) {
  return async (req: Request, ctx: C) => {
    try {
      const session = await getSession();
      if (!session) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
      const body = await handler(session, req, ctx);
      return body instanceof Response ? body : NextResponse.json(body);
    } catch (err) {
      return errorResponse(err);
    }
  };
}

export function errorResponse(err: unknown) {
  if (err instanceof ServiceError) {
    // 5xx from a service (or unreachable) is a dependency failure for the browser; 4xx keeps its meaning.
    const status = err.status >= 500 ? 502 : err.status;
    return NextResponse.json({ error: "service_error", service: err.service, detail: err.message }, { status });
  }
  console.error("[edge] unexpected error", err);
  return NextResponse.json({ error: "internal_error" }, { status: 500 });
}
