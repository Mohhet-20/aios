"use client";

import { usePathname } from "next/navigation";
import { FlaskConical } from "lucide-react";

/** Routes that render live service data. Every other shell route is labelled as a preview. */
export const LIVE_ROUTES = [
  "/dashboard",
  "/agents",
  "/prompts/library",
  "/workflows",
  "/tools/plugins",
  "/evaluation",
  "/models/registry",
  "/models/playground",
];

/** Shown by the shell layout on every route that isn't in LIVE_ROUTES. */
export function PreviewNotice() {
  const pathname = usePathname();
  if (!pathname || LIVE_ROUTES.includes(pathname)) return null;
  return <PreviewBanner />;
}

/**
 * Marks a page whose figures are illustrative: the screen design is complete, but it is not yet wired to its
 * service. Live pages never show this; see README "What is live in the console".
 */
export function PreviewBanner({ service }: { service?: string }) {
  return (
    <div
      role="note"
      className="mb-5 flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-900 dark:text-amber-200"
    >
      <FlaskConical className="h-3.5 w-3.5 shrink-0" />
      <span>
        <strong>Preview:</strong> illustrative data. This screen isn&apos;t wired to
        {service ? ` the ${service}` : " its service"} yet; the live pages are Dashboard, Agents, Prompt Library,
        Workflows, Tools, Evaluation, Model Registry and Model Playground.
      </span>
    </div>
  );
}
