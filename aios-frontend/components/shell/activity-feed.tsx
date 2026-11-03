"use client";

import { X, History } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useUIStore } from "@/stores/ui-store";
import { activity } from "@/lib/mock-data";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { formatDistanceToNow } from "date-fns";

/** Slide-over drawer showing recent org-wide activity (prompt promotions,
 *  workflow edits, tool registrations). Kept in the shell (not a page) so it
 *  can be opened from anywhere as ambient awareness of what teammates are
 *  doing — important once dozens of people share one workspace. */
export function ActivityFeed() {
  const { activityFeedOpen, toggleActivityFeed } = useUIStore();

  return (
    <AnimatePresence>
      {activityFeedOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/20"
            onClick={toggleActivityFeed}
          />
          <motion.aside
            initial={{ x: 360 }}
            animate={{ x: 0 }}
            exit={{ x: 360 }}
            transition={{ type: "tween", duration: 0.2 }}
            className="fixed right-0 top-0 z-50 flex h-screen w-[360px] flex-col border-l border-border bg-card shadow-xl"
          >
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4" />
                <p className="text-sm font-semibold">Activity</p>
              </div>
              <Button variant="ghost" size="icon" onClick={toggleActivityFeed}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <ScrollArea className="flex-1">
              <ul className="divide-y divide-border">
                {activity.map((a) => (
                  <li key={a.id} className="px-4 py-3 text-sm">
                    <p>
                      <span className="font-medium">{a.actor}</span> <span className="text-muted-foreground">{a.action}</span>{" "}
                      <span className="font-medium">{a.target}</span>
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{formatDistanceToNow(new Date(a.createdAt), { addSuffix: true })}</p>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
