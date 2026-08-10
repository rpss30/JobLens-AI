import { CardSkeleton, Skeleton } from "@/components/ui/States";

export default function SkillsLoading() {
  return (
    <>
      <div className="space-y-2">
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <CardSkeleton rows={8} />
        <CardSkeleton rows={8} />
      </div>
      <CardSkeleton rows={6} />
    </>
  );
}
