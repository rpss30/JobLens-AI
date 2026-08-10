import { apiFetch, apiUpload, buildQueryString } from "@/lib/api/client";
import type {
  AnalysisRun,
  AnalyzeRequest,
  AnalyzeResponse,
  CreateAnalysisRunRequest,
  DatasetSummary,
  DeleteDatasetResult,
  FilterOptions,
  HealthResponse,
  JobListResponse,
  MarketInsights,
  RenameDatasetResult,
  SearchMode,
  SortOrder,
  UploadDatasetResult,
} from "@/lib/api/types";

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export function getFilterOptions(
  datasetName?: string | null,
): Promise<FilterOptions> {
  return apiFetch<FilterOptions>(
    `/filter-options${buildQueryString({ dataset_name: datasetName })}`,
  );
}

export function getDatasets(): Promise<DatasetSummary[]> {
  return apiFetch<DatasetSummary[]>("/datasets");
}

export function uploadDataset(formData: FormData): Promise<UploadDatasetResult> {
  // Multipart bodies must set their own boundary, so apiFetch is bypassed here.
  return apiUpload<UploadDatasetResult>("/datasets", formData);
}

export function renameDataset(
  datasetName: string,
  newName: string,
): Promise<RenameDatasetResult> {
  return apiFetch<RenameDatasetResult>(
    `/datasets/${encodeURIComponent(datasetName)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ new_name: newName }),
    },
  );
}

export function deleteDataset(
  datasetName: string,
): Promise<DeleteDatasetResult> {
  return apiFetch<DeleteDatasetResult>(
    `/datasets/${encodeURIComponent(datasetName)}`,
    { method: "DELETE" },
  );
}

export interface JobQuery {
  datasetName?: string | null;
  targetRoles?: string[];
  searchQuery?: string;
  searchMode?: SearchMode;
  location?: string;
  experienceLevel?: string;
  sortBy?: string;
  sortOrder?: SortOrder;
  limit?: number;
  offset?: number;
}

export function getJobs(query: JobQuery = {}): Promise<JobListResponse> {
  return apiFetch<JobListResponse>(
    `/jobs${buildQueryString({
      dataset_name: query.datasetName,
      target_roles: query.targetRoles,
      search_query: query.searchQuery,
      search_mode: query.searchMode,
      location: query.location,
      experience_level: query.experienceLevel,
      sort_by: query.sortBy,
      sort_order: query.sortOrder,
      limit: query.limit,
      offset: query.offset,
    })}`,
  );
}

export interface MarketInsightsQuery {
  datasetName?: string | null;
  targetRoles?: string[];
  searchQuery?: string;
  searchMode?: SearchMode;
  location?: string;
  experienceLevel?: string;
  topN?: number;
}

export function getMarketInsights(
  query: MarketInsightsQuery = {},
): Promise<MarketInsights> {
  return apiFetch<MarketInsights>("/market-insights", {
    method: "POST",
    body: JSON.stringify({
      dataset_name: query.datasetName ?? null,
      target_roles: query.targetRoles ?? [],
      search_query: query.searchQuery ?? "",
      search_mode: query.searchMode ?? "tfidf",
      location: query.location ?? "Any",
      experience_level: query.experienceLevel ?? "Any",
      top_n: query.topN ?? 10,
    }),
  });
}

export function analyzeJobs(
  request: AnalyzeRequest,
): Promise<AnalyzeResponse> {
  return apiFetch<AnalyzeResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function getAnalysisRuns(
  query: { datasetName?: string | null; sortBy?: string; sortOrder?: SortOrder } = {},
): Promise<AnalysisRun[]> {
  return apiFetch<AnalysisRun[]>(
    `/analysis-runs${buildQueryString({
      dataset_name: query.datasetName,
      sort_by: query.sortBy,
      sort_order: query.sortOrder,
    })}`,
  );
}

export function getAnalysisRun(analysisRunId: number): Promise<AnalysisRun> {
  return apiFetch<AnalysisRun>(`/analysis-runs/${analysisRunId}`);
}

export function createAnalysisRun(
  request: CreateAnalysisRunRequest,
): Promise<AnalysisRun> {
  return apiFetch<AnalysisRun>("/analysis-runs", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function renameAnalysisRun(
  analysisRunId: number,
  newName: string,
): Promise<{ id: number; name: string; renamed: boolean }> {
  return apiFetch(`/analysis-runs/${analysisRunId}`, {
    method: "PATCH",
    body: JSON.stringify({ new_name: newName }),
  });
}

export function deleteAnalysisRun(
  analysisRunId: number,
): Promise<{ id: number; deleted: boolean }> {
  return apiFetch(`/analysis-runs/${analysisRunId}`, { method: "DELETE" });
}
