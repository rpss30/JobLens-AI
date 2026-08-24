"use client";

import { useState } from "react";

import { SingleSelectCombobox } from "@/components/ui/SingleSelectCombobox";

/**
 * One filter control, holding its own choice until the form is submitted.
 *
 * The Jobs filters are a plain GET form, so the value has to reach the server
 * as a form field rather than through a router push. The combobox keeps a
 * hidden input for exactly that.
 */
export function FilterCombobox({
  id,
  name,
  value,
  options,
  placeholder,
  onChanged,
}: {
  id: string;
  name: string;
  value: string;
  options: { value: string; label: string }[];
  placeholder: string;
  /**
   * The choice is held in state and submitted through a hidden input, so a
   * native change event never reaches the form. Anything that needs to know
   * the reader touched this has to be told.
   */
  onChanged?: () => void;
}) {
  const [chosen, setChosen] = useState(value);
  const [lastValue, setLastValue] = useState(value);

  // A filter applied elsewhere re-renders this in place, so follow the URL
  // rather than keeping whatever was picked before.
  if (value !== lastValue) {
    setLastValue(value);
    setChosen(value);
  }

  return (
    <SingleSelectCombobox
      id={id}
      name={name}
      value={chosen}
      onChange={(next) => {
        setChosen(next);
        onChanged?.();
      }}
      options={options}
      placeholder={placeholder}
      size="compact"
    />
  );
}
