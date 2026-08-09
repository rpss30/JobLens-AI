import { getHealth } from "@/lib/api/endpoints";

/** Small live indicator so a stopped backend is obvious rather than confusing. */
export async function ApiStatus() {
  let isOnline = false;

  try {
    const health = await getHealth();
    isOnline = health.status === "ok";
  } catch {
    isOnline = false;
  }

  return (
    <span className="flex items-center gap-1.5">
      <span
        className={`h-2 w-2 rounded-full ${isOnline ? "bg-positive" : "bg-danger"}`}
        aria-hidden="true"
      />
      <span className="hidden text-xs text-text-muted sm:inline">
        {isOnline ? "API online" : "API offline"}
      </span>
      <span className="sr-only">
        {isOnline
          ? "The JobLens API is reachable."
          : "The JobLens API is unreachable."}
      </span>
    </span>
  );
}
