import type { CreateAnalysisRunRequest } from "@/lib/api/types";
import type { StoredAnalysis } from "@/context/AnalysisContext";

/**
 * Writing a result to history, from wherever it is asked for.
 *
 * The save button asks, and so does the prompt that appears when a result is
 * about to be thrown away, so the request they send lives here rather than in
 * whichever of them happened to be written first.
 */
export function buildAnalysisRunPayload(
  analysis: StoredAnalysis,
): CreateAnalysisRunRequest {
  const { request, response } = analysis;

  return {
    name: "",
    dataset_name: response.dataset_name,
    target_roles: request.target_roles,
    location: request.location,
    experience_level: request.experience_level,
    candidate_experience: request.candidate_experience,
    current_skills:
      response.resume_analysis?.combined_skills.slice(0, 50) ??
      request.current_skills,
    best_role: response.best_role,
    weighted_match_score: response.weighted_match_score,
    top_missing_skill: response.top_missing_skill,
    jobs_analyzed: response.jobs_analyzed,
    recommended_skills: response.recommended_skills.map((item) => item.skill),
    // The API caps saved role scores, so send the ranked head only.
    role_scores: response.role_scores.slice(0, 20) as unknown as Record<
      string,
      unknown
    >[],
  };
}

/** The reason it did not save, or nothing at all when it did. */
export async function saveAnalysisRun(
  analysis: StoredAnalysis,
): Promise<string | null> {
  try {
    const response = await fetch("/proxy/analysis-runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildAnalysisRunPayload(analysis)),
    });

    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as {
        detail?: string;
      } | null;

      return body?.detail ?? "This result could not be saved.";
    }

    return null;
  } catch {
    return "Could not reach JobLens. Check your connection.";
  }
}
