import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";

export default function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="That page does not exist, or the record it points to is no longer saved."
      action={
        <Link href="/">
          <Button>Back to overview</Button>
        </Link>
      }
    />
  );
}
