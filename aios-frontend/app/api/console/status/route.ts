import { platformStatus } from "@/lib/server/console";
import { withSession } from "@/lib/server/route";

export const GET = withSession(async () => platformStatus());
