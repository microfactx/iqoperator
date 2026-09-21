import * as React from "react"
import { cn } from "@/lib/utils"

// Pílula de status (corr status-pill, MIT — port sem lucide, dot CSS puro)
export function StatusPill({
  status,
  label,
  className,
}: {
  status: "online" | "degraded" | "offline"
  label: string
  className?: string
}) {
  const dot =
    status === "online" ? "#3DD68C" : status === "degraded" ? "#FACC15" : "#FF5470"
  const text =
    status === "online" ? "text-success" : status === "degraded" ? "text-[#FACC15]" : "text-destructive"
  const bg =
    status === "online"
      ? "bg-success/10 border-success/25"
      : status === "degraded"
        ? "bg-[#FACC15]/10 border-[#FACC15]/25"
        : "bg-destructive/10 border-destructive/25"

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-bold tracking-widest uppercase",
        bg,
        text,
        className
      )}
    >
      <span className="relative flex h-2 w-2">
        {status === "online" && (
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
            style={{ backgroundColor: dot }}
          />
        )}
        <span
          className="relative inline-flex h-2 w-2 rounded-full"
          style={{ backgroundColor: dot, boxShadow: `0 0 8px ${dot}` }}
        />
      </span>
      {label}
    </span>
  )
}