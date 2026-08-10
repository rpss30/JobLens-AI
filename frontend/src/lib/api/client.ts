/**
 * Server-side fetch wrapper for the JobLens FastAPI backend.
 *
 * Import this from Server Components and route handlers only. The API base URL
 * stays on the server, and client components reach the backend through the
 * route handlers under app/proxy rather than calling FastAPI directly.
 *
 * Those handlers live under /proxy rather than /api because in production the
 * reverse proxy owns /api/* and forwards it to FastAPI, so an /api route here
 * would never be reached by the browser.
 */

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getApiBaseUrl(): string {
  const configuredUrl = process.env.JOBLENS_API_URL?.trim();

  return (configuredUrl || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export type QueryValue = string | number | boolean | null | undefined | string[];

export function buildQueryString(query: Record<string, QueryValue>): string {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }

    if (Array.isArray(value)) {
      value.filter(Boolean).forEach((item) => params.append(key, item));
      continue;
    }

    params.set(key, String(value));
  }

  const queryString = params.toString();

  return queryString ? `?${queryString}` : "";
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };

    if (typeof body.detail === "string" && body.detail.trim()) {
      return body.detail;
    }

    // FastAPI validation errors arrive as a list of issue objects.
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const firstIssue = body.detail[0] as { msg?: string };

      if (typeof firstIssue.msg === "string") {
        return firstIssue.msg;
      }
    }
  } catch {
    // Fall through to the generic message below.
  }

  return `Request failed with status ${response.status}.`;
}

/**
 * Multipart uploads must let fetch set the Content-Type boundary, so this
 * skips the JSON header apiFetch applies.
 */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ApiError(
      "Could not reach the JobLens API. Check that the backend is running.",
      503,
    );
  }

  if (!response.ok) {
    throw new ApiError(await readErrorDetail(response), response.status);
  }

  return (await response.json()) as T;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Could not reach the JobLens API. Check that the backend is running.",
      503,
    );
  }

  if (!response.ok) {
    throw new ApiError(await readErrorDetail(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
