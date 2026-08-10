import { CardSkeleton, Skeleton, StatRowSkeleton } from "@/components/ui/States";

export default function OverviewLoading() {
  return (
    <>
      <div className="space-y-2">
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-4 w-72 max-w-full" />
      </div>
      <StatRowSkeleton />
      <div className="grid gap-6 lg:grid-cols-2">
        <CardSkeleton rows={5} />
        <CardSkeleton rows={5} />
      </div>
    </>
  );
}
