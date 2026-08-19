import { Button } from "@/components/ui/Button";
import { Field, controlClassName } from "@/components/ui/Field";
import { FilterCombobox } from "@/components/domain/FilterCombobox";
import type { FilterOptions } from "@/lib/api/types";

export interface JobFilterValues {
  q: string;
  location: string;
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
          <FilterCombobox
            id="job-location"
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

        <Field label="Company" htmlFor="job-company">
          <FilterCombobox
            id="job-company"
            name="company"
            placeholder="Any company"
            value={values.company}
            options={[
              { value: "Any", label: "Any company" },
              ...(values.company !== "Any" &&
              !filterOptions.companies.includes(values.company)
                ? [{ value: values.company, label: values.company }]
                : []),
              ...filterOptions.companies.map((option) => ({
                value: option,
                label: option,
              })),
            ]}
          />
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
