import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { LiveState } from "@/components/shared/live-state";
import { PreviewNotice } from "@/components/shared/preview-banner";
import { ApiError } from "@/services/api-client";
import { humanize, parseServiceDate, timeAgo } from "@/lib/utils";

const pathname = vi.hoisted(() => ({ current: "/dashboard" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

afterEach(cleanup);

describe("LiveState", () => {
  it("shows a service failure instead of hiding it", () => {
    render(
      <LiveState query={{ data: undefined, isLoading: false, error: new ApiError("agent service is unreachable", 502, "agent") }}>
        {() => <p>data</p>}
      </LiveState>,
    );
    expect(screen.getByRole("alert").textContent).toContain("agent service: agent service is unreachable");
    expect(screen.queryByText("data")).toBeNull();
  });

  it("renders the empty state for an empty list", () => {
    render(
      <LiveState query={{ data: [], isLoading: false, error: null }} isEmpty={(d: unknown[]) => d.length === 0} empty="No agents yet.">
        {() => <p>data</p>}
      </LiveState>,
    );
    expect(screen.getByText("No agents yet.")).toBeTruthy();
  });

  it("renders the data once loaded", () => {
    render(<LiveState query={{ data: ["a"], isLoading: false, error: null }}>{(d) => <p>{d.join()}</p>}</LiveState>);
    expect(screen.getByText("a")).toBeTruthy();
  });
});

describe("PreviewNotice", () => {
  it("is hidden on live routes", () => {
    pathname.current = "/agents";
    const { container } = render(<PreviewNotice />);
    expect(container.textContent).toBe("");
  });

  it("labels every other route as a preview", () => {
    pathname.current = "/analytics";
    render(<PreviewNotice />);
    expect(screen.getByRole("note").textContent).toContain("illustrative data");
  });
});

describe("date and label helpers", () => {
  it("reads offset-less service timestamps as UTC", () => {
    expect(parseServiceDate("2026-11-03T16:54:26").toISOString()).toBe("2026-11-03T16:54:26.000Z");
    expect(parseServiceDate("2026-11-03T16:54:26+00:00").toISOString()).toBe("2026-11-03T16:54:26.000Z");
  });

  it("formats relative times", () => {
    const now = Date.now();
    expect(timeAgo(new Date(now - 30_000).toISOString())).toBe("just now");
    expect(timeAgo(new Date(now - 2 * 3600_000).toISOString())).toBe("2 hours ago");
    expect(timeAgo(null)).toBeNull();
  });

  it("humanizes enum values", () => {
    expect(humanize("knowledge_pipeline")).toBe("Knowledge pipeline");
  });
});
