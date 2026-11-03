import { PageHeader } from "@/components/shared/page-header";
import { PromptStudio } from "@/features/prompts/prompt-studio";

export default function PromptStudioPage() {
  return (
    <div>
      <PageHeader title="Prompt Studio" description="Author, preview, version, and promote prompts with evaluation-gated releases." />
      <PromptStudio />
    </div>
  );
}
