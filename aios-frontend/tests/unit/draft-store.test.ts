import { beforeEach, describe, expect, it } from "vitest";
import { useDraftStore } from "@/stores/draft-store";

beforeEach(() => {
  useDraftStore.setState({ drafts: {} });
  window.localStorage.clear();
});

describe("useDraftStore", () => {
  it("saves a draft under its key", () => {
    useDraftStore.getState().saveDraft("prompt:pr_1", '{"template":"hello"}');
    expect(useDraftStore.getState().drafts["prompt:pr_1"]).toBe('{"template":"hello"}');
  });

  it("overwrites an existing draft for the same key", () => {
    useDraftStore.getState().saveDraft("prompt:pr_1", "v1");
    useDraftStore.getState().saveDraft("prompt:pr_1", "v2");
    expect(useDraftStore.getState().drafts["prompt:pr_1"]).toBe("v2");
  });

  it("keeps drafts for different keys independent", () => {
    useDraftStore.getState().saveDraft("prompt:pr_1", "a");
    useDraftStore.getState().saveDraft("workflow:wf_1", "b");
    expect(useDraftStore.getState().drafts).toEqual({
      "prompt:pr_1": "a",
      "workflow:wf_1": "b",
    });
  });

  it("clears a draft by key without touching others", () => {
    useDraftStore.getState().saveDraft("prompt:pr_1", "a");
    useDraftStore.getState().saveDraft("workflow:wf_1", "b");
    useDraftStore.getState().clearDraft("prompt:pr_1");
    expect(useDraftStore.getState().drafts).toEqual({ "workflow:wf_1": "b" });
  });

  it("clearing a non-existent key is a safe no-op", () => {
    useDraftStore.getState().saveDraft("prompt:pr_1", "a");
    useDraftStore.getState().clearDraft("does-not-exist");
    expect(useDraftStore.getState().drafts).toEqual({ "prompt:pr_1": "a" });
  });
});
