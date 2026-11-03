import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { StatusBar } from "@/components/shell/status-bar";
import { ActivityFeed } from "@/components/shell/activity-feed";
import { CommandPalette } from "@/components/shell/command-palette";
import { PreviewNotice } from "@/components/shared/preview-banner";

/**
 * Application shell shared by every authenticated route. This is the layer
 * every page in app/(shell)/* mounts inside — pages themselves only render
 * their own content via PageHeader + feature components, never chrome.
 */
export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto scrollbar-thin px-6 py-6 3xl:px-10">
          <PreviewNotice />
          {children}
        </main>
        <StatusBar />
      </div>
      <ActivityFeed />
      <CommandPalette />
    </div>
  );
}
