import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/server/route";
import { callService } from "@/lib/server/services";
import { getSession } from "@/lib/server/session";

export async function GET() {
  try {
    const session = await getSession();
    if (!session) return NextResponse.json({ authenticated: false }, { status: 401 });
    const organization = session.organizationId
      ? await callService<{ id: string; name: string }>("identity", `/api/v1/organizations/${encodeURIComponent(session.organizationId)}`)
          .then((o) => ({ id: o.id, name: o.name }))
          .catch(() => null)
      : null;
    return NextResponse.json({
      authenticated: true,
      user: { id: session.userId, email: session.email, displayName: session.displayName },
      organizationId: session.organizationId,
      organization,
    });
  } catch (err) {
    return errorResponse(err);
  }
}
