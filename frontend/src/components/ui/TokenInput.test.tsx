import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TokenInput } from "@/components/ui/TokenInput";

const SUGGESTIONS = ["python", "sql", "docker", "machine learning"];

function renderTokenInput(overrides: Partial<Parameters<typeof TokenInput>[0]> = {}) {
  const onChange = vi.fn();

  render(
    <TokenInput
      id="skills"
      label="Skills you have"
      values={[]}
      suggestions={SUGGESTIONS}
      onChange={onChange}
      {...overrides}
    />,
  );

  return { onChange, input: screen.getByLabelText("Skills you have") };
}

describe("TokenInput", () => {
  it("adds every skill from one paste instead of only the last", async () => {
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput();

    await user.click(input);
    await user.paste("python, sql; docker");

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(["python", "sql", "docker"]);
  });

  it("prefers the dataset's spelling over what the user typed", async () => {
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput();

    await user.type(input, "DOCKER{Enter}");

    expect(onChange).toHaveBeenCalledWith(["docker"]);
  });

  it("rejects a value outside the list when custom values are not allowed", async () => {
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput({ allowCustomValues: false });

    await user.type(input, "kubernetes{Enter}");

    expect(onChange).not.toHaveBeenCalled();
    expect(
      screen.getByText(/"kubernetes" is not in the list/i),
    ).toBeInTheDocument();
  });

  it("still accepts a listed value when custom values are not allowed", async () => {
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput({ allowCustomValues: false });

    await user.type(input, "sql{Enter}");

    expect(onChange).toHaveBeenCalledWith(["sql"]);
  });

  it("ignores a duplicate regardless of casing", async () => {
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput({ values: ["docker"] });

    await user.type(input, "Docker{Enter}");

    expect(onChange).not.toHaveBeenCalled();
  });

  it("accepts the suggestion on screen when enter is pressed", async () => {
    // Typing "mach" listed "machine learning" and then rejected it, because
    // enter committed the raw text rather than the match being shown.
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput({ allowCustomValues: false });

    await user.type(input, "mach{Enter}");

    expect(onChange).toHaveBeenCalledWith(["machine learning"]);
  });

  it("does not guess when what was typed only appears mid-suggestion", async () => {
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput({ allowCustomValues: false });

    // "o" appears inside python and docker but starts neither, so silently
    // picking one would put a skill the reader never chose on their profile.
    await user.type(input, "o{Enter}");

    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByText(/is not in the list/i)).toBeInTheDocument();
  });

  it("disables the input once the limit is reached", () => {
    const { input } = renderTokenInput({ values: ["python"], maxValues: 1 });

    expect(input).toBeDisabled();
    expect(input).toHaveAttribute("placeholder", "Limit of 1 reached");
  });

  it("removes the last value on backspace with an empty draft", async () => {
    const user = userEvent.setup();
    const { onChange, input } = renderTokenInput({ values: ["python", "sql"] });

    await user.click(input);
    await user.keyboard("{Backspace}");

    expect(onChange).toHaveBeenCalledWith(["python"]);
  });
});
