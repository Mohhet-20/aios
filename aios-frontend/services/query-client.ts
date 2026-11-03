import { QueryClient } from "@tanstack/react-query";

/**
 * Central React Query client. Defaults favor a "dashboard" workload: data
 * is allowed to be a few seconds stale (avoids refetch storms when many
 * widgets mount at once) but refetches on window focus so a user tabbing
 * back into AIOS sees fresh state.
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: true,
        retry: 1,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
