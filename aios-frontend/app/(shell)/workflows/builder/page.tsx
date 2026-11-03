import { PageHeader } from "@/components/shared/page-header";
import { WorkflowBuilder } from "@/features/workflows/workflow-builder";

export default function WorkflowBuilderPage() {
  return (
    <div>
      <PageHeader title="Workflow Builder" description="Compose agents, tools, and conditions into an executable pipeline." />
      <WorkflowBuilder />
    </div>
  );
}
