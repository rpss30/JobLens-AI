import { describe, expect, it } from "vitest";

import { DEFAULT_DATASET, resolveDataset } from "@/lib/datasets";

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
