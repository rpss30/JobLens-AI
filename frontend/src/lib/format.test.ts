import { describe, expect, it } from "vitest";

import {
  formatCount,
  formatDate,
  formatDatasetLabel,
  formatPercent,
  formatSkill,
  locationTag,
} from "@/lib/format";

describe("formatCount", () => {
  it("groups thousands", () => {
    expect(formatCount(1234)).toBe("1,234");
    expect(formatCount(0)).toBe("0");
  });
});

describe("formatPercent", () => {
  it("defaults to one fraction digit and appends a percent sign", () => {
    expect(formatPercent(33.333)).toBe("33.3%");
  });

  it("honours an explicit precision", () => {
    expect(formatPercent(33.333, 0)).toBe("33%");
  });
});

describe("formatDate", () => {
  it("returns the input unchanged when it is not a date", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
    expect(formatDate("")).toBe("");
  });

  it("formats a parseable date", () => {
    // Asserting the exact day would be flaky: "2026-08-10" parses as UTC
    // midnight, so a runner behind UTC renders the previous day. The year is
    // enough to prove formatting ran rather than passing the string through.
    const formatted = formatDate("2026-08-10");

    expect(formatted).toContain("2026");
    expect(formatted).not.toBe("2026-08-10");
  });
});

describe("formatSkill", () => {
  it("spells known acronyms the way people write them", () => {
    expect(formatSkill("aws")).toBe("AWS");
    expect(formatSkill("ci/cd")).toBe("CI/CD");
    expect(formatSkill("apis")).toBe("APIs");
  });

  it("leaves spellings the extractor already capitalized", () => {
    expect(formatSkill("PostgreSQL")).toBe("PostgreSQL");
    expect(formatSkill("PyTorch")).toBe("PyTorch");
  });

  it("title-cases each word of a lowercase phrase", () => {
    expect(formatSkill("machine learning")).toBe("Machine Learning");
  });

  it("passes through blank input", () => {
    expect(formatSkill("   ")).toBe("");
  });
});

describe("formatDatasetLabel", () => {
  it("uses friendly names for bundled datasets", () => {
    expect(formatDatasetLabel("canada_snapshot")).toBe("Canada snapshot");
    expect(formatDatasetLabel("early_career_global")).toBe("Global early career");
    expect(formatDatasetLabel("local_sample")).toBe("Local sample");
  });

  it("shows an uploaded dataset's own name", () => {
    expect(formatDatasetLabel("my_upload")).toBe("my_upload");
  });
});

describe("locationTag", () => {
  const places = ["Madison, WI", "Seattle, WA", "Austin, TX"];

  it("names the first place and counts the rest", () => {
    expect(locationTag(places, "")).toEqual({
      lead: "Madison, WI",
      extraCount: 2,
    });
  });

  it("leads with the place the reader asked for", () => {
    expect(locationTag(places, "", "Seattle, WA")).toEqual({
      lead: "Seattle, WA",
      extraCount: 2,
    });
  });

  it("ignores a filter the posting does not answer", () => {
    expect(locationTag(places, "", "Toronto, ON")).toEqual({
      lead: "Madison, WI",
      extraCount: 2,
    });
  });

  it("falls back to the raw field when nothing was parsed", () => {
    expect(locationTag([], "Somewhere odd")).toEqual({
      lead: "Somewhere odd",
      extraCount: 0,
    });
  });

  it("gives nothing when the posting names nowhere", () => {
    expect(locationTag([], "")).toBeNull();
  });
});
