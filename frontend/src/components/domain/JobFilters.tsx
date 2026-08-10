import { Button } from "@/components/ui/Button";
import { Field, controlClassName } from "@/components/ui/Field";
import type { FilterOptions } from "@/lib/api/types";

export interface JobFilterValues {
  q: string;
  location: string;
  level: string;
  sort: string;
  order: string;
}

const SORT_OPTIONS = [
  { value: "search_relevance", label: "Relevance" },
  { value: "date_posted", label: "Date posted" },
  { value: "title", label: "Title" },
  { value: "company", label: "Company" },
  { value: "location", label: "Location" },
];

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
  return (
    <form
      method="get"
      action="/jobs"
      className="rounded-xl border border-border bg-surface p-5"
    >
      <input type="hidden" name="dataset" value={datasetName} />

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
              className={controlClassName}
            />
          </Field>
        </div>

        <Field label="Location" htmlFor="job-location">
          <select
            id="job-location"
            name="location"
            defaultValue={values.location}
            className={controlClassName}
          >
            <option value="Any">Any location</option>
            {filterOptions.locations.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Experience level" htmlFor="job-level">
          <select
            id="job-level"
            name="level"
            defaultValue={values.level}
            className={controlClassName}
          >
            <option value="Any">Any level</option>
            {filterOptions.experience_levels.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Sort by" htmlFor="job-sort">
          <select
            id="job-sort"
            name="sort"
            defaultValue={values.sort}
            className={controlClassName}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm">
          Apply filters
        </Button>
        <a
          href={`/jobs?dataset=${encodeURIComponent(datasetName)}`}
          className="text-sm font-medium text-text-muted hover:text-text"
        >
          Reset
        </a>
      </div>
    </form>
  );
}
