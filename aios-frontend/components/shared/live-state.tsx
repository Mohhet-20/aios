"use client";

import type { ReactNode } from "react";
import { AlertTriangle, Inbox } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/services/api-client";

interface LiveStateProps<T> {
  query: { data: T | undefined; isLoading: boolean; error: unknown };
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
  skeleton?: ReactNode;
  children: (data: T) => ReactNode;
}

/** Loading, error and empty states for data that comes from a live service, so a failure is never hidden. */
export function LiveState<T>({ query, isEmpty, empty, skeleton, children }: LiveStateProps<T>) {
  if (query.isLoading) {
    return <>{skeleton ?? <Skeleton className="h-32 w-full" />}</>;
  }
  if (query.error) {
    const err = query.error;
    const service = err instanceof ApiError && err.service ? `${err.service} service: ` : "";
    return (
      <div role="alert" className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        <div>
          <p className="font-medium">Couldn&apos;t load this from the platform.</p>
          <p className="text-muted-foreground">
            {service}
            {err instanceof Error ? err.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }
  if (query.data === undefined) return null;
  if (isEmpty?.(query.data)) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
        <Inbox className="h-5 w-5" />
        {empty ?? "Nothing here yet."}
      </div>
    );
  }
  return <>{children(query.data)}</>;
}
