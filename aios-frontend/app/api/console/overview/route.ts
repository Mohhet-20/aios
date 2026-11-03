import { platformStatus, resources } from "@/lib/server/console";
import { withSession } from "@/lib/server/route";
import type { Overview } from "@/types/live";

/** Dashboard summary: real counts from five services plus live readiness of all twenty, fetched in parallel. */
export const GET = withSession(async (session): Promise<Overview> => {
  const [agents, prompts, workflows, tools, evaluations, datasets, services] = await Promise.all([
    resources.agents(session),
    resources.prompts(session),
    resources.workflows(session),
    resources.tools(session),
    resources.evaluations(session),
    resources.datasets(session),
    platformStatus(),
  ]);
  return {
    counts: {
      agents: agents.length,
      activeAgents: agents.filter((a) => a.status === "active").length,
      prompts: prompts.length,
      workflows: workflows.length,
      tools: tools.length,
      evaluations: evaluations.length,
      datasets: datasets.length,
    },
    services,
  };
});
