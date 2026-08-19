import { describe, expect, it } from "vitest";

import { fitLabel, textWidth } from "./RoleSkillsExplorer";

/*
 * jsdom has no canvas, so textWidth falls back to its estimate. That is the
 * point: the search has to behave for whatever the measurer reports, and the
 * estimate is deterministic enough to assert against.
 */
const SIZE = 15;
const WEIGHT = 700;

const widthOf = (text: string) => textWidth(text, SIZE, WEIGHT);

describe("fitLabel", () => {
  it("leaves a label alone when it already fits", () => {
    expect(fitLabel("Go", widthOf("Go") + 1, SIZE, WEIGHT)).toBe("Go");
  });

  it("never returns something wider than the room it was given", () => {
    // Lengths well past anything a skill name reaches, so the search is not
    // being checked only against the cases that happen to exist today.
    const labels = [
      "",
      "R",
      "Kubernetes",
      "Statistical Modeling",
      "a".repeat(200),
      "Machine Learning ".repeat(30),
    ];

    for (const label of labels) {
      for (const room of [0, 1, 12, 40, 120, 400]) {
        const fitted = fitLabel(label, room, SIZE, WEIGHT);

        // An ellipsis on its own is the floor: below that there is nothing to
        // show, and the tooltip still carries the full name.
        if (fitted !== "…") {
          expect(widthOf(fitted)).toBeLessThanOrEqual(room);
        }

        expect(label.startsWith(fitted.replace("…", "").trimEnd())).toBe(true);
      }
    }
  });

  it("gives more of the label as the room grows", () => {
    const label = "Statistical Modeling";
    const narrow = fitLabel(label, 40, SIZE, WEIGHT);
    const wide = fitLabel(label, 120, SIZE, WEIGHT);

    expect(wide.length).toBeGreaterThan(narrow.length);
    expect(fitLabel(label, 10_000, SIZE, WEIGHT)).toBe(label);
  });
});
