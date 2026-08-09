import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface Column<Row> {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: Row) => ReactNode;
}

interface DataTableProps<Row> {
  columns: Column<Row>[];
  rows: Row[];
  getRowKey: (row: Row, index: number) => string;
  caption?: string;
  emptyMessage?: string;
  /** Only set for tables with enough columns to need horizontal scrolling. */
  minWidthClassName?: string;
}

export function DataTable<Row>({
  columns,
  rows,
  getRowKey,
  caption,
  emptyMessage = "No rows to show.",
  minWidthClassName = "min-w-full",
}: DataTableProps<Row>) {
  if (rows.length === 0) {
    return <p className="px-5 py-6 text-sm text-text-muted">{emptyMessage}</p>;
  }

  return (
    // Wide tables scroll inside their own container, never the page body.
    <div className="overflow-x-auto">
      <table className={cn("w-full border-collapse text-sm", minWidthClassName)}>
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        <thead>
          <tr className="border-b border-border">
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={cn(
                  "px-5 py-2.5 text-xs font-medium uppercase tracking-wide text-text-subtle",
                  column.align === "right" ? "text-right" : "text-left",
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={getRowKey(row, index)}
              className="border-b border-border last:border-0"
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={cn(
                    "px-5 py-3 text-text",
                    column.align === "right"
                      ? "text-right tabular-nums"
                      : "text-left",
                  )}
                >
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
