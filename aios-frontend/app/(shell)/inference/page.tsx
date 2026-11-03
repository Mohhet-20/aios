import { PageHeader } from "@/components/shared/page-header";
import { InferenceStudio } from "@/features/inference/inference-studio";

export default function InferencePage() {
  return (
    <div>
      <PageHeader title="Inference Studio" description="Test agents and prompts interactively with live streaming responses." />
      <InferenceStudio />
    </div>
  );
}
