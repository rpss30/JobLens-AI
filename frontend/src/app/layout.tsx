import type { Metadata } from "next";
import { Nunito } from "next/font/google";

import { ApiStatus } from "@/components/layout/ApiStatus";
import { AppShell } from "@/components/layout/AppShell";
import type { DatasetOption } from "@/components/layout/DatasetSwitcher";
import { AnalysisProvider } from "@/context/AnalysisContext";
import { ToastProvider } from "@/context/ToastContext";
import { getDatasets } from "@/lib/api/endpoints";
import { LOCAL_DATASETS } from "@/lib/datasets";

import "./globals.css";

/*
 * The design calls for SF Pro Rounded, which Apple licenses for its own
 * platforms only and which cannot be shipped as a web font. --font-sans asks
 * for it by keyword first, so Apple devices render the real face; Nunito is
 * the closest freely licensable rounded fallback for everyone else.
 */
const roundedSans = Nunito({
  variable: "--font-rounded",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "JobLens",
  description:
    "Job market intelligence for role fit, skill gaps, and hiring demand.",
};

async function loadDatasetOptions(): Promise<DatasetOption[]> {
  try {
    const datasets = await getDatasets();

    return [
      ...LOCAL_DATASETS,
      ...datasets.map((dataset) => ({
        value: dataset.name,
        label: dataset.name,
        group: "PostgreSQL datasets",
      })),
    ];
  } catch {
    // PostgreSQL is optional locally, so fall back to the bundled datasets.
    return LOCAL_DATASETS;
  }
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const datasets = await loadDatasetOptions();

  return (
    <html lang="en" className={`${roundedSans.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">
        <ToastProvider>
          <AnalysisProvider>
            <AppShell datasets={datasets} statusSlot={<ApiStatus />}>
              {children}
            </AppShell>
          </AnalysisProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
