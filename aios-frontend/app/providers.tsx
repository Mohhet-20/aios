"use client";

import * as React from "react";
import { ThemeProvider } from "next-themes";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@/services/query-client";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";

/**
 * Single composition root for every cross-cutting client provider:
 * theming (light/dark/system), server-state caching (React Query), tooltip
 * delay-group behavior, and the global toast renderer. Kept as one file so
 * the provider order (which matters — theme must wrap everything that reads
 * CSS vars) is defined in exactly one place.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(() => createQueryClient());

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={200}>
          {children}
          <Toaster />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
