"use client";

import { useState } from "react";

import {
  deleteDatasetAction,
  renameDatasetAction,
  type DatasetActionResult,
} from "@/app/datasets/actions";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { controlClassName } from "@/components/ui/Field";
import { useToast } from "@/context/ToastContext";
import type { DatasetSummary } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

const USER_MANAGED_SOURCE = "uploaded_csv";

function formatSourceType(sourceType: string): string {
  if (sourceType === USER_MANAGED_SOURCE) {
    return "Uploaded CSV";
  }

  if (sourceType === "sample_csv") {
    return "Protected sample";
  }

  return sourceType.replace(/_/g, " ");
}

export function DatasetRow({ dataset }: { dataset: DatasetSummary }) {
  const { showToast } = useToast();
  const [isRenaming, setIsRenaming] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [newName, setNewName] = useState(dataset.name);
  const [isBusy, setIsBusy] = useState(false);

  const isUserManaged = dataset.source_type === USER_MANAGED_SOURCE;

  async function runAction(action: () => Promise<DatasetActionResult>) {
    setIsBusy(true);

    const result = await action();

    if (result.ok) {
      setIsRenaming(false);
      setIsConfirmingDelete(false);
      showToast(result.message);
    } else {
      showToast(result.message, "error");
    }

    setIsBusy(false);
  }

  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-text">
            {dataset.name}
          </p>
          <p className="mt-0.5 text-xs text-text-muted">
            Added {formatDate(dataset.created_at)}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={isUserManaged ? "accent" : "neutral"}>
            {formatSourceType(dataset.source_type)}
          </Badge>

          {isUserManaged ? (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsRenaming((open) => !open)}
                aria-expanded={isRenaming}
              >
                Rename
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={isBusy}
                onClick={() => setIsConfirmingDelete(true)}
              >
                Delete
              </Button>
            </>
          ) : (
            <span className="text-xs text-text-subtle">Locked</span>
          )}
        </div>
      </div>

      {isRenaming ? (
        <form
          className="mt-3 flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            runAction(() => renameDatasetAction(dataset.name, newName));
          }}
        >
          <div className="min-w-0 flex-1">
            <label
              htmlFor={`rename-${dataset.name}`}
              className="block text-sm font-medium text-text"
            >
              New name
            </label>
            <input
              id={`rename-${dataset.name}`}
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              required
              className={`mt-1.5 ${controlClassName}`}
            />
          </div>
          <Button type="submit" size="sm" disabled={isBusy}>
            {isBusy ? "Saving…" : "Save name"}
          </Button>
        </form>
      ) : null}

      <ConfirmDialog
        open={isConfirmingDelete}
        title={`Delete ${dataset.name}?`}
        description="This permanently removes the dataset and its job postings. Saved analyses that used it will keep their results, but you will not be able to re-run them against this data."
        confirmLabel="Delete dataset"
        isBusy={isBusy}
        onCancel={() => setIsConfirmingDelete(false)}
        onConfirm={() => runAction(() => deleteDatasetAction(dataset.name))}
      />
    </li>
  );
}
