import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/ui/States";

export default function OverviewPage() {
  return (
    <>
      <PageHeader
        title="Overview"
        description="Role fit, skill gaps, and hiring demand across the selected job market dataset."
      />
      <EmptyState
        title="No analysis yet"
        description="Run a candidate analysis to see role fit, skill gaps, and matching postings here."
      />
    </>
  );
}
