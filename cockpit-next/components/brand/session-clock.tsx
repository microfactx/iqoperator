"use client"
import * as React from "react"
import { cn } from "@/lib/utils"

// Relógio de sessão: hora local + UTC + sessões ASIA/LONDON/NY (implementação própria)
const SESSIONS = [
  { name: "ASIA", open: 0, close: 8 },
  { name: "LONDON", open: 7, close: 16 },
  { name: "NY", open: 12, close: 21 },
]

export function SessionClock({ className }: { className?: string }) {
  const [now, setNow] = React.useState(() => new Date())
  React.useEffect(() => {
    const i = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(i)
  }, [])

  const utcH = now.getUTCHours() + now.getUTCMinutes() / 60
  const pad = (n: number) => String(n).padStart(2, "0")
  const local = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  const utc = `${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())}:${pad(now.getUTCSeconds())} UTC`

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="text-right leading-tight">
        <div className="font-bold text-lg text-foreground mono tabular-nums">{local}</div>
        <div className="text-[11px] text-muted mono">{utc}</div>
      </div>
      <div className="flex gap-1.5">
        {SESSIONS.map((s) => {
          const open = utcH >= s.open && utcH < s.close
          return (
            <span
              key={s.name}
              title={`${s.name} ${s.open}h–${s.close}h UTC`}
              className={cn(
                "rounded border px-1.5 py-0.5 text-[10px] font-bold tracking-wider mono",
                open
                  ? "border-success/30 bg-success/10 text-success"
                  : "border-border bg-background/60 text-muted"
              )}
            >
              {s.name}
            </span>
          )
        })}
      </div>
    </div>
  )
}