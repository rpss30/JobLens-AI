import { apiFetch, buildQueryString } from "@/lib/api/client";
import type {
  AnalysisRun,
  AnalyzeRequest,
  AnalyzeResponse,
  CreateAnalysisRunRequest,
  DatasetSummary,
  FilterOptions,
  HealthResponse,
  JobListResponse,
  MarketInsights,
  SearchMode,
  SortOrder,
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
