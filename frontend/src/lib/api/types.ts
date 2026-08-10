/**
 * Mirrors the Pydantic response models in src/api/schemas.py.
 *
 * FastAPI owns all analysis, matching, and validation logic. These types only
 * describe the shapes the frontend consumes.
 */

export type SearchMode = "tfidf" | "semantic" | "hybrid";

export type SortOrder = "asc" | "desc";

export interface HealthResponse {
  status: string;
}

export interface DatasetSummary {
  name: string;
  source_type: string;
  created_at: string;
}

export interface UploadDatasetResult {
  dataset_name: string;
  job_count: number;
}

export interface RenameDatasetResult {
  old_name: string;
  new_name: string;
  renamed: boolean;
}

export interface DeleteDatasetResult {
  dataset_name: string;
  deleted: boolean;
}

export interface DatasetSnapshotSummary {
  job_count: number;
  company_count: number;
  location_count: number;
  refreshed_date: string;
}

export interface FilterOptions {
  dataset_name: string;
  target_roles: string[];
  role_categories: string[];
  skills: string[];
  locations: string[];
  experience_levels: string[];
  summary: DatasetSnapshotSummary;
}

export interface JobListing {
  job_id: string;
  title: string;
  company: string;
  location: string;
  experience_level: string;
  role_category: string;
  employment_type: string;
  workplace_type: string;
  is_remote: boolean;
  date_posted: string;
  source: string;
  source_url: string;
  skills: string[];
  search_relevance: number;
}

export interface JobListResponse {
  dataset_name: string;
  total: number;
  limit: number;
  offset: number;
  jobs: JobListing[];
}

export interface SkillDemand {
  skill: string;
  job_count: number;
}

export interface RoleSkillImportance {
  role_category: string;
  skill: string;
  job_count: number;
  role_weight: number;
  weighted_importance: number;
}

export interface LocationDemand {
  location: string;
  job_count: number;
}

export interface CompanyDemand {
  company: string;
  job_count: number;
}

export interface RoleDistribution {
  role_category: string;
  job_count: number;
}

export interface MarketInsights {
  dataset_name: string;
  jobs_analyzed: number;
  skill_demand: SkillDemand[];
  role_skill_importance: RoleSkillImportance[];
  jobs_by_location: LocationDemand[];
  top_companies: CompanyDemand[];
  role_distribution: RoleDistribution[];
}

export interface RecommendedSkill {
  skill: string;
  score: number;
  job_count: number;
  avg_weight: number;
}

export interface RoleScore {
  role_category: string;
  sample_size: number;
  weighted_match_score: number;
  unweighted_match_score: number;
  matched_weight: number;
  total_possible_weight: number;
  matched_skills: string[];
  related_skills: string[];
  missing_skills: string[];
  representative_job_count: number;
  sample_confidence: string;
  headline_eligible: boolean;
}

export interface JobMatch {
  title: string;
  company: string;
  location: string;
  experience_level: string;
  role_category: string;
  source: string;
  source_url: string;
  search_relevance: number;
  semantic_relevance: number;
  tfidf_relevance: number;
  search_mode: string;
  job_match_score: number;
  skill_match_score: number;
  candidate_experience: string;
  required_experience: string;
  required_experience_years: number | null;
  experience_requirement_source: string;
  experience_fit: string;
  experience_fit_score: number | null;
  matched_skills_count: number;
  related_skills_count: number;
  missing_skills_count: number;
  matched_skills_preview: string;
  related_skills_preview: string;
  missing_skills_preview: string;
}

export interface LearningPriority {
  skill: string;
  priority_score: number;
  job_count: number;
  reason: string;
}

export interface ResumeJobMatch {
  title: string;
  company: string;
  location: string;
  role_category: string;
  fit_score: number;
  skill_fit_score: number;
  resume_similarity: number;
  matched_skills: string[];
  missing_skills: string[];
  explanation: string;
}

export interface ResumeAnalysis {
  provided: boolean;
  privacy_note: string;
  resume_skills: string[];
  combined_skills: string[];
  experience_areas: string[];
  project_keywords: string[];
  fit_score: number;
  matched_skills: string[];
  missing_skills: string[];
  learning_priorities: LearningPriority[];
  suggested_resume_keywords: string[];
  top_matching_jobs: ResumeJobMatch[];
  explanation: string;
}

export interface AnalyzeRequest {
  current_skills: string[];
  resume_text: string;
  target_roles: string[];
  search_query: string;
  search_mode: SearchMode;
  location: string;
  experience_level: string;
  candidate_experience: string;
  top_n: number;
  dataset_name: string | null;
}

export interface AnalyzeResponse {
  dataset_name: string;
  best_role: string;
  weighted_match_score: number;
  top_missing_skill: string;
  jobs_analyzed: number;
  recommended_skills: RecommendedSkill[];
  role_scores: RoleScore[];
  top_matching_jobs: JobMatch[];
  resume_analysis: ResumeAnalysis | null;
}

export interface AnalysisRun {
  id: number;
  name: string;
  dataset_name: string;
  target_roles: string[];
  location: string;
  experience_level: string;
  current_skills: string[];
  best_role: string | null;
  weighted_match_score: number | null;
  top_missing_skill: string | null;
  jobs_analyzed: number;
  recommended_skills: string[];
  role_scores: Record<string, unknown>[];
  created_at: string;
}

export interface CreateAnalysisRunRequest {
  name: string;
  dataset_name: string;
  target_roles: string[];
  location: string;
  experience_level: string;
  current_skills: string[];
  best_role: string | null;
  weighted_match_score: number | null;
  top_missing_skill: string | null;
  jobs_analyzed: number;
  recommended_skills: string[];
  role_scores: Record<string, unknown>[];
}
