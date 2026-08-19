import { describe, expect, it } from "vitest";

import { splitJobDescription } from "./jobDescription";

describe("splitJobDescription", () => {
  it("returns one block when the wording gives no signal", () => {
    const text = "We are hiring an engineer. The team is small and remote.";

    expect(splitJobDescription(text)).toEqual([
      { kind: "paragraph", text },
    ]);
  });

  it("starts a new block at a section heading", () => {
    const blocks = splitJobDescription(
      "We build tools for teams. Requirements You have written Go before.",
    );

    expect(blocks).toEqual([
      { kind: "paragraph", text: "We build tools for teams." },
      { kind: "heading", text: "Requirements" },
      { kind: "paragraph", text: "You have written Go before." },
    ]);
  });

  it("leaves a heading phrase alone when it opens a sentence", () => {
    // "Our team" and "Benefits" begin real sentences here. Treating them as
    // headings split each one into a title and a dangling fragment.
    const text =
      "We ship weekly. Our team is a collection of engineers. Benefits and total rewards vary by region.";

    expect(splitJobDescription(text)).toEqual([{ kind: "paragraph", text }]);
  });

  it("still treats the phrase as a heading when a new thought follows", () => {
    const blocks = splitJobDescription(
      "We ship weekly. Our team Engineers who care about the craft.",
    );

    expect(blocks).toEqual([
      { kind: "paragraph", text: "We ship weekly." },
      { kind: "heading", text: "Our team" },
      { kind: "paragraph", text: "Engineers who care about the craft." },
    ]);
  });

  it("turns inline markers into list items", () => {
    const blocks = splitJobDescription(
      "Benefits - Health cover from day one - Four weeks of leave",
    );

    // The list opens straight after the heading, so both are items rather
    // than one of them being the prose that introduces the list.
    expect(blocks).toEqual([
      { kind: "heading", text: "Benefits" },
      { kind: "bullet", text: "Health cover from day one" },
      { kind: "bullet", text: "Four weeks of leave" },
    ]);
  });

  it("leaves a hyphen used as punctuation alone", () => {
    const text = "We are a well - known team that ships often.";

    expect(splitJobDescription(text)).toEqual([{ kind: "paragraph", text }]);
  });

  it("has nothing to say about an empty description", () => {
    expect(splitJobDescription("   ")).toEqual([]);
  });
});
