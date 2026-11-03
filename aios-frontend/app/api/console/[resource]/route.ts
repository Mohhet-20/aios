import { NextResponse } from "next/server";
import { resources, type ResourceName } from "@/lib/server/console";
import { withSession } from "@/lib/server/route";

export const GET = withSession(async (session, _req, ctx: { params: Promise<{ resource: string }> }) => {
  const { resource } = await ctx.params;
  if (!Object.hasOwn(resources, resource)) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  return resources[resource as ResourceName](session);
});
