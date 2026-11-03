import { beforeEach, describe, expect, it } from "vitest";
import { useUIStore } from "@/stores/ui-store";

// zustand stores are singletons — reset to known defaults before each test
// so tests don't leak state into each other (persist middleware also writes
// to jsdom's localStorage between runs).
beforeEach(() => {
  useUIStore.setState({
    sidebarCollapsed: false,
    commandPaletteOpen: false,
    activityFeedOpen: false,
  });
  window.localStorage.clear();
});

describe("useUIStore", () => {
  it("toggles sidebar collapse state", () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  it("sets command palette open state directly", () => {
    useUIStore.getState().setCommandPaletteOpen(true);
    expect(useUIStore.getState().commandPaletteOpen).toBe(true);
    useUIStore.getState().setCommandPaletteOpen(false);
    expect(useUIStore.getState().commandPaletteOpen).toBe(false);
  });

  it("toggles activity feed drawer independently of sidebar", () => {
    useUIStore.getState().toggleSidebar();
    useUIStore.getState().toggleActivityFeed();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
    expect(useUIStore.getState().activityFeedOpen).toBe(true);
  });
});
