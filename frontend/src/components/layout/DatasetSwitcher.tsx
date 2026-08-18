"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useId, useTransition } from "react";

import { DEFAULT_DATASET } from "@/lib/datasets";

export interface DatasetOption {
  value: string;
  label: string;
  group: string;
}

/**
 * The active dataset lives in the URL so Server Components can read it and so
 * a filtered view stays shareable.
 *
 * The id is generated rather than fixed because the shell mounts one switcher
 * in the sidebar and another in the mobile drawer.
 */
export function DatasetSwitcher({ datasets }: { datasets: DatasetOption[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const selectId = useId();

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
    <div className="space-y-1.5">
      <label
        htmlFor={selectId}
        className="block text-xs font-medium text-text-subtle"
      >
        Dataset
      </label>
      <select
        id={selectId}
        value={activeDataset}
        disabled={isPending}
        onChange={(event) => handleChange(event.target.value)}
        className="h-9 w-full min-w-0 rounded-lg border border-border bg-surface px-2.5 text-sm text-text disabled:opacity-60"
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
