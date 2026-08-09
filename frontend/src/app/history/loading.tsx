import { CardSkeleton, Skeleton } from "@/components/ui/States";

export default function HistoryLoading() {
  return (
    <>
      <div className="space-y-2">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      <CardSkeleton rows={6} />
    </>
  );
}
