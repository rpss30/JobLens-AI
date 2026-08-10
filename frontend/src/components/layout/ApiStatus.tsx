import { InfoTooltip } from "@/components/ui/InfoTooltip";
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
        className={`h-2 w-2 rounded-full ${
          isOnline ? "bg-status-online" : "bg-status-offline"
        }`}
        aria-hidden="true"
      />

      {/* The word is hidden on narrow screens, but the info icon stays so the
          explanation is still reachable there. */}
      <InfoTooltip
        label={
          <span className="hidden sm:inline">
            {isOnline ? "Connected" : "Disconnected"}
          </span>
        }
        variant="plain"
      >
        {isOnline ? (
          <>
            <strong className="text-text">JobLens is connected</strong>
            <br />
            The service that reads job postings and works out your matches is
            responding normally, so everything on the site is up to date.
          </>
        ) : (
          <>
            <strong className="text-text">JobLens is disconnected</strong>
            <br />
            The service that reads job postings is not responding right now.
            Job lists and skill matches may fail to load or show older
            information until it comes back.
          </>
        )}
      </InfoTooltip>
    </span>
  );
}
