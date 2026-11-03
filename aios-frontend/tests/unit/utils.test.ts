import { describe, expect, it } from "vitest";
import { cn, formatCurrency, formatLatency, formatNumber } from "@/lib/utils";

describe("cn", () => {
  it("merges class names and resolves conflicting Tailwind utilities", () => {
    expect(cn("px-2", "py-1")).toBe("px-2 py-1");
    // twMerge should keep only the last conflicting padding-x utility.
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("drops falsy values", () => {
    expect(cn("a", false && "b", undefined, null, "c")).toBe("a c");
  });
});

describe("formatCurrency", () => {
  it("formats whole dollar amounts with 2 decimal places", () => {
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
  });

  it("uses up to 4 decimal places for sub-dollar amounts (LLM token costs)", () => {
    expect(formatCurrency(0.0032)).toBe("$0.0032");
  });
});

describe("formatNumber", () => {
  it("compacts large numbers", () => {
    expect(formatNumber(1500)).toBe("1.5K");
    expect(formatNumber(2_300_000)).toBe("2.3M");
  });

  it("leaves small numbers unchanged", () => {
    expect(formatNumber(42)).toBe("42");
  });
});

describe("formatLatency", () => {
  it("renders sub-second latencies in milliseconds", () => {
    expect(formatLatency(250)).toBe("250ms");
    expect(formatLatency(999)).toBe("999ms");
  });

  it("renders latencies of 1s or more in seconds with 2 decimals", () => {
    expect(formatLatency(1000)).toBe("1.00s");
    expect(formatLatency(2540)).toBe("2.54s");
  });
});
