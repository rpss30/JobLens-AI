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

  const statusTitle = isOnline
    ? "JobLens is connected to its data service."
    : "JobLens cannot reach its data service, so results may not load.";

  return (
    <span className="flex items-center gap-1.5" title={statusTitle}>
      <span
        className={`h-2 w-2 rounded-full ${
          isOnline ? "bg-status-online" : "bg-status-offline"
        }`}
        aria-hidden="true"
      />
      <span className="hidden text-xs text-text-muted sm:inline">
        {isOnline ? "Connected" : "Disconnected"}
      </span>
      <span className="sr-only">{statusTitle}</span>
    </span>
  );
}
