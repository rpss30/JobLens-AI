"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { SingleSelectCombobox } from "@/components/ui/SingleSelectCombobox";
import {
  ANY_FILTER_VALUE,
  EMPTY_MATCH_FILTERS,
  activeMatchFilterCount,
  experienceFitLabel,
  type MatchFilterOptions,
  type MatchFilterValues,
} from "@/lib/matches";

function toOptions(
  values: string[],
  anyLabel: string,
  toLabel: (value: string) => string = (value) => value,
) {
  return [
    { value: ANY_FILTER_VALUE, label: anyLabel },
    ...values.map((value) => ({ value, label: toLabel(value) })),
  ];
}

/**
 * Narrowing the matched jobs, in the shape the Jobs filters use.
 *
 * The Jobs panel is a GET form because that list lives in the URL. A result
 * does not, so this holds the choices until Apply rather than submitting
 * anywhere. Applying is still a separate step: changing four dropdowns one at
 * a time would otherwise rebuild the list four times.
 */
export function MatchFilters({
  options,
  values,
  onApply,
}: {
  options: MatchFilterOptions;
  values: MatchFilterValues;
  onApply: (values: MatchFilterValues) => void;
}) {
  const [draft, setDraft] = useState(values);

  const isDirty = (Object.keys(draft) as (keyof MatchFilterValues)[]).some(
    (key) => draft[key] !== values[key],
  );
  const hasFilters = activeMatchFilterCount(draft) > 0;

  function choose(key: keyof MatchFilterValues) {
    return (value: string) => setDraft({ ...draft, [key]: value });
  }

  return (
    <div
      // Its own card on a narrow screen; from lg it is the top of the one it
      // shares with the list, so only the rule under it survives.
      className="rounded-xl border border-border bg-surface p-5 lg:rounded-none lg:border-x-0 lg:border-t-0 lg:bg-transparent"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Field label="Category" htmlFor="match-category">
          <SingleSelectCombobox
            id="match-category"
            size="compact"
            placeholder="Any category"
            value={draft.category}
            onChange={choose("category")}
            options={toOptions(options.categories, "Any category")}
          />
        </Field>

        <Field label="Experience Level" htmlFor="match-fit">
          <SingleSelectCombobox
            id="match-fit"
            size="compact"
            placeholder="Any level"
            value={draft.fit}
            onChange={choose("fit")}
            // Not the posting's own seniority label: what the reader wants
            // from this list is how far each job is out of reach.
            options={toOptions(options.fits, "Any level", experienceFitLabel)}
          />
        </Field>

        <Field label="Location" htmlFor="match-location">
          <SingleSelectCombobox
            id="match-location"
            size="compact"
            placeholder="Any location"
            value={draft.location}
            onChange={choose("location")}
            options={toOptions(options.locations, "Any location")}
          />
        </Field>

        <Field label="Company" htmlFor="match-company">
          <SingleSelectCombobox
            id="match-company"
            size="compact"
            placeholder="Any company"
            value={draft.company}
            onChange={choose("company")}
            options={toOptions(options.companies, "Any company")}
          />
        </Field>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button size="sm" disabled={!isDirty} onClick={() => onApply(draft)}>
          Apply filters
        </Button>
        {/* Nothing to clear reads as nothing to press, rather than a button
            that quietly rebuilds the same list. */}
        {hasFilters ? (
          <button
            type="button"
            onClick={() => {
              setDraft(EMPTY_MATCH_FILTERS);
              onApply(EMPTY_MATCH_FILTERS);
            }}
            className="text-sm font-medium text-text-muted transition-colors hover:text-text"
          >
            Reset
          </button>
        ) : (
          <span
            aria-disabled="true"
            className="cursor-not-allowed text-sm font-medium text-text-subtle opacity-55"
          >
            Reset
          </span>
        )}
      </div>
    </div>
  );
}
