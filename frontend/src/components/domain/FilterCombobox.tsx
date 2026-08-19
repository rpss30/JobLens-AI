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
}: {
  id: string;
  name: string;
  value: string;
  options: { value: string; label: string }[];
  placeholder: string;
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
      onChange={setChosen}
      options={options}
      placeholder={placeholder}
      size="compact"
    />
  );
}
