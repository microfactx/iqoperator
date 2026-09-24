import { cn } from "@/lib/utils";
import type { ComponentType, ReactNode } from "react";

type IconProps = {
  size?: number | string;
  className?: string;
  [key: string]: any;
};

type SectionHeadingProps = {
  icon: ComponentType<IconProps> | ComponentType<any>;
  title: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
};

export function SectionHeading({ icon: Icon, title, hint, action, className }: SectionHeadingProps) {
  return (
    <div className={cn("flex items-center justify-between gap-3", className)}>
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="h-7 w-7 shrink-0 rounded-md bg-accent/10 text-accent flex items-center justify-center">
          <Icon size={15} />
        </span>
        <div className="min-w-0">
          <h2 className="font-semibold text-foreground text-sm leading-tight truncate">{title}</h2>
          {hint ? <p className="text-xs text-muted leading-tight truncate">{hint}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0 flex items-center gap-2">{action}</div> : null}
    </div>
  );
}
