import { CardSkeleton, Skeleton } from "@/components/ui/States";

export default function JobsLoading() {
  return (
    <>
      <div className="space-y-2">
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <Skeleton className="h-36 w-full rounded-xl" />
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <CardSkeleton key={index} rows={3} />
        ))}
      </div>
    </>
  );
}
