import { CardSkeleton, Skeleton } from "@/components/ui/States";

export default function AnalyzeLoading() {
  return (
    <>
      <div className="space-y-2">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <CardSkeleton rows={6} />
        <CardSkeleton rows={6} />
      </div>
    </>
  );
}
