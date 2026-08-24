import { describe, expect, it } from "vitest";

import { DEFAULT_DATASET, resolveDataset, withDataset } from "@/lib/datasets";

describe("resolveDataset", () => {
  it("falls back to the default when the param is missing or blank", () => {
    expect(resolveDataset(undefined)).toBe(DEFAULT_DATASET);
    expect(resolveDataset("")).toBe(DEFAULT_DATASET);
    expect(resolveDataset("   ")).toBe(DEFAULT_DATASET);
  });

  it("uses an explicit dataset name", () => {
    expect(resolveDataset("local_sample")).toBe("local_sample");
  });

  it("takes the first value when a param is repeated in the URL", () => {
    expect(resolveDataset(["local_sample", "canada_snapshot"])).toBe(
      "local_sample",
    );
  });

  it("falls back when a repeated param is empty", () => {
    expect(resolveDataset([])).toBe(DEFAULT_DATASET);
  });
});

describe("withDataset", () => {
  it("leaves a link alone when no dataset is active", () => {
    expect(withDataset("/analyze", null)).toBe("/analyze");
    expect(withDataset("/analyze", undefined)).toBe("/analyze");
    expect(withDataset("/analyze", "  ")).toBe("/analyze");
  });

  it("carries the active dataset so navigation does not reset it", () => {
    expect(withDataset("/analyze", "local_sample")).toBe(
      "/analyze?dataset=local_sample",
    );
  });

  it("escapes a dataset name that is not URL safe", () => {
    expect(withDataset("/jobs", "my jobs&more")).toBe(
      "/jobs?dataset=my%20jobs%26more",
    );
  });

  it("appends to a link that already has a query", () => {
    expect(withDataset("/jobs?q=python", "local_sample")).toBe(
      "/jobs?q=python&dataset=local_sample",
    );
  });
});
