import type { ComponentType } from "react";

type IconProps = {
  size?: number;
  className?: string;
};

type EmptyStateProps = {
  icon: ComponentType<IconProps>;
  title: string;
  hint?: string;
};

export function EmptyState({ icon: Icon, title, hint }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-background/60 text-muted">
        <Icon size={20} />
      </span>
      <p className="text-sm text-foreground">{title}</p>
      {hint ? <p className="text-xs text-muted max-w-xs">{hint}</p> : null}
    </div>
  );
}
