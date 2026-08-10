import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  apiFetch,
  apiUpload,
  buildQueryString,
  getApiBaseUrl,
} from "@/lib/api/client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("buildQueryString", () => {
  it("returns an empty string when nothing is set", () => {
    expect(buildQueryString({})).toBe("");
    expect(buildQueryString({ location: undefined, role: null, q: "" })).toBe("");
  });

  it("prefixes a question mark and encodes values", () => {
    expect(buildQueryString({ q: "data engineer" })).toBe("?q=data+engineer");
  });

  it("repeats a key for array values and drops blank entries", () => {
    expect(buildQueryString({ skill: ["python", "", "sql"] })).toBe(
      "?skill=python&skill=sql",
    );
  });

  it("keeps falsy-but-meaningful values", () => {
    expect(buildQueryString({ offset: 0, remote: false })).toBe(
      "?offset=0&remote=false",
    );
  });
});

describe("getApiBaseUrl", () => {
  it("defaults to the local backend when unset", () => {
    vi.stubEnv("JOBLENS_API_URL", "");

    expect(getApiBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("uses the configured URL and strips trailing slashes", () => {
    vi.stubEnv("JOBLENS_API_URL", "http://api:8000///");

    expect(getApiBaseUrl()).toBe("http://api:8000");
  });
});

describe("apiFetch", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("JOBLENS_API_URL", "http://api:8000");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("returns the parsed body and sends JSON headers", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: "ok" }));

    await expect(apiFetch("/health")).resolves.toEqual({ status: "ok" });

    const [url, init] = fetchMock.mock.calls[0];

    expect(url).toBe("http://api:8000/health");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json" });
  });

  it("resolves to undefined for a 204 rather than parsing an empty body", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(apiFetch("/analysis-runs/1")).resolves.toBeUndefined();
  });

  it("surfaces a string detail from the API", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "Dataset not found." }, 404),
    );

    await expect(apiFetch("/datasets/missing")).rejects.toThrowError(
      new ApiError("Dataset not found.", 404),
    );
  });

  it("surfaces the first message from a FastAPI validation error list", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          detail: [
            { msg: "Input should be 'tfidf', 'semantic' or 'hybrid'" },
            { msg: "second issue" },
          ],
        },
        422,
      ),
    );

    await expect(apiFetch("/analyze", { method: "POST" })).rejects.toThrowError(
      "Input should be 'tfidf', 'semantic' or 'hybrid'",
    );
  });

  it("falls back to a generic message when the error body is not JSON", async () => {
    fetchMock.mockResolvedValue(new Response("<html>oops</html>", { status: 500 }));

    await expect(apiFetch("/jobs")).rejects.toThrowError(
      "Request failed with status 500.",
    );
  });

  it("reports an unreachable backend as a 503 instead of leaking the fetch error", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));

    const error = await apiFetch("/health").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(503);
    expect((error as ApiError).message).toContain("Could not reach");
  });
});

describe("apiUpload", () => {
  it("lets fetch set the multipart boundary by sending no Content-Type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ name: "demo" }));

    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("JOBLENS_API_URL", "http://api:8000");

    const formData = new FormData();
    formData.append("file", new Blob(["a,b\n1,2"]), "jobs.csv");

    await expect(apiUpload("/datasets", formData)).resolves.toEqual({
      name: "demo",
    });

    const [, init] = fetchMock.mock.calls[0];

    expect(init.headers).toBeUndefined();
    expect(init.body).toBe(formData);

    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });
});
