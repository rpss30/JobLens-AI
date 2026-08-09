"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";

import { DEFAULT_DATASET } from "@/lib/datasets";

export interface DatasetOption {
  value: string;
  label: string;
  group: string;
}

/**
 * The active dataset lives in the URL so Server Components can read it and so
 * a filtered view stays shareable.
 */
export function DatasetSwitcher({ datasets }: { datasets: DatasetOption[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const activeDataset = searchParams.get("dataset") ?? DEFAULT_DATASET;

  const groups = Array.from(new Set(datasets.map((dataset) => dataset.group)));

  function handleChange(nextDataset: string) {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("dataset", nextDataset);

    startTransition(() => {
      router.push(`${pathname}?${nextParams.toString()}`);
    });
  }

  return (
    <div className="flex min-w-0 items-center gap-2">
      <label
        htmlFor="dataset-switcher"
        className="hidden text-xs font-medium text-text-subtle sm:block"
      >
        Dataset
      </label>
      <select
        id="dataset-switcher"
        value={activeDataset}
        disabled={isPending}
        onChange={(event) => handleChange(event.target.value)}
        className="h-9 min-w-0 max-w-[8.5rem] rounded-lg border border-border bg-surface px-2.5 text-sm text-text disabled:opacity-60 sm:max-w-[13rem]"
      >
        {groups.map((group) => (
          <optgroup key={group} label={group}>
            {datasets
              .filter((dataset) => dataset.group === group)
              .map((dataset) => (
                <option key={dataset.value} value={dataset.value}>
                  {dataset.label}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}
