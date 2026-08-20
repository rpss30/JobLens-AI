"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Field, controlClassName } from "@/components/ui/Field";
import { FilterCombobox } from "@/components/domain/FilterCombobox";
import type { FilterOptions } from "@/lib/api/types";

export interface JobFilterValues {
  q: string;
  location: string;
  category: string;
  company: string;
  level: string;
  sort: string;
  order: string;
}

/**
 * A plain GET form: filters live in the URL, so results are shareable and the
 * page keeps working without client JavaScript.
 */
export function JobFilters({
  filterOptions,
  values,
  datasetName,
}: {
  filterOptions: FilterOptions;
  values: JobFilterValues;
  datasetName: string;
}) {
  // Sort and order are not filters: they change the reading order, not which
  // postings are in it, so neither makes a reset worth offering.
  // Applying is only worth offering once something has actually been
  // changed. Otherwise the button reloads the list it is already showing.
  const [isDirty, setIsDirty] = useState(false);
  const markDirty = () => setIsDirty(true);

  // Everything the panel is currently applying, minus the employer, so the
  // chip can drop just that one and leave the rest standing.
  const clearCompanyParams = new URLSearchParams({
    dataset: datasetName,
    q: values.q,
    location: values.location,
    category: values.category,
    level: values.level,
    sort: values.sort,
    order: values.order,
    filters: "open",
  });
  const clearCompanyHref = `/jobs?${clearCompanyParams.toString()}`;

  const hasFilters = Boolean(
    values.q.trim() ||
      [values.location, values.category, values.level, values.company].some(
        (value) => value && value !== "Any",
      ),
  );

  return (
    <form
      method="get"
      action="/jobs"
      className="rounded-xl border border-border bg-surface p-5"
    >
      <input type="hidden" name="dataset" value={datasetName} />
      {/* Chosen beside the heading rather than in here, but it still has to
          survive a filter change. */}
      <input type="hidden" name="sort" value={values.sort} />
      <input type="hidden" name="order" value={values.order} />
      {/* Top Hiring Companies narrows by employer, which has no control here
          because the categories took its place. It still has to survive a
          change to the filters beside it. */}
      <input type="hidden" name="company" value={values.company} />
      {/* Applying a filter is not a reason to put the panel away. */}
      <input type="hidden" name="filters" value="open" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <div className="xl:col-span-2">
          <Field label="Search jobs" htmlFor="job-search">
            <input
              id="job-search"
              type="search"
              name="q"
              maxLength={200}
              defaultValue={values.q}
              placeholder="Try a job title, skill, or company"
              onChange={markDirty}
              className={controlClassName}
            />
          </Field>
        </div>

        <Field label="Location" htmlFor="job-location">
          <FilterCombobox
            id="job-location"
            onChanged={markDirty}
            name="location"
            placeholder="Any location"
            value={values.location}
            options={[
              { value: "Any", label: "Any location" },
              // Market Insights links here with a place it counted under,
              // which is rarely one of the dataset's own strings.
              ...(values.location !== "Any" &&
              !filterOptions.locations.includes(values.location)
                ? [{ value: values.location, label: values.location }]
                : []),
              ...filterOptions.locations.map((option) => ({
                value: option,
                label: option,
              })),
            ]}
          />
        </Field>

        <Field label="Experience level" htmlFor="job-level">
          <FilterCombobox
            id="job-level"
            onChanged={markDirty}
            name="level"
            placeholder="Any level"
            value={values.level}
            options={[
              { value: "Any", label: "Any level" },
              ...filterOptions.experience_levels.map((option) => ({
                value: option,
                label: option,
              })),
            ]}
          />
        </Field>

        <Field label="Category" htmlFor="job-category">
          <FilterCombobox
            id="job-category"
            onChanged={markDirty}
            name="category"
            placeholder="Any category"
            value={values.category}
            options={[
              { value: "Any", label: "Any category" },
              // Role Distribution links here with the category it counted
              // under, which a refreshed dataset may no longer list.
              ...(values.category !== "Any" &&
              !filterOptions.role_categories.includes(values.category)
                ? [{ value: values.category, label: values.category }]
                : []),
              ...filterOptions.role_categories.map((option) => ({
                value: option,
                label: option,
              })),
            ]}
          />
        </Field>
      </div>

      {/* The employer has no control of its own, so an active one says so
          here rather than narrowing the list invisibly. */}
      {values.company !== "Any" ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-muted py-1 pl-3 pr-1.5 text-sm text-text">
            <span className="text-text-muted">Company:</span>
            {values.company}
            <a
              href={clearCompanyHref}
              aria-label={`Stop filtering by ${values.company}`}
              className="inline-flex size-5 items-center justify-center rounded-full text-text-muted transition-colors hover:bg-border hover:text-text"
            >
              <span aria-hidden="true">&times;</span>
            </a>
          </span>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm" disabled={!isDirty}>
          Apply filters
        </Button>
        {/* Nothing to clear reads as nothing to press, rather than a link
            that quietly reloads the same list. */}
        {hasFilters ? (
          <a
            href={`/jobs?dataset=${encodeURIComponent(
              datasetName,
            )}&filters=open`}
            className="text-sm font-medium text-text-muted hover:text-text"
          >
            Reset
          </a>
        ) : (
          <span
            aria-disabled="true"
            className="cursor-not-allowed text-sm font-medium text-text-subtle opacity-55"
          >
            Reset
          </span>
        )}
      </div>
    </form>
  );
}
