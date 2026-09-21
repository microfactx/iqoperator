import { cn } from "@/lib/utils";

type CardSkeletonProps = {
  lines?: number;
  className?: string;
};

export function CardSkeleton({ lines = 3, className }: CardSkeletonProps) {
  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4 animate-pulse", className)} aria-hidden="true">
      <div className="h-4 w-1/3 bg-muted/20 rounded" />
      <div className="mt-3 space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className="h-3 bg-muted/10 rounded" />
        ))}
      </div>
    </div>
  );
}
