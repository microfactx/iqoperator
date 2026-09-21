import * as React from "react"
import { cn } from "@/lib/utils"

export function TradesFeed({
  trades,
  className,
}: {
  trades: any[]
  className?: string
}) {
  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4 flex flex-col", className)}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium">Atividade Recente</h2>
        <span className="text-[11px] text-muted">últimas {trades.length}</span>
      </div>

      {trades.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-sm text-muted">
          Sem atividade ainda
        </div>
      ) : (
        <div className="flex-1 overflow-auto max-h-[280px] flex flex-col gap-2 pr-1">
          {trades.map((t, i) => {
            const profit = parseFloat(t.profit)
            const isWin = !isNaN(profit) && profit > 0
            const isLoss = !isNaN(profit) && profit < 0
            const signal = String(t.signal || "").toLowerCase()
            return (
              <div
                key={i}
                className="flex items-center gap-3 bg-background/60 rounded px-3 py-2 text-xs"
              >
                <span className="text-muted mono w-14 shrink-0">
                  {String(t.time || "").split(" ").slice(-1)[0] || "—"}
                </span>
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded font-bold uppercase shrink-0",
                    signal.includes("call")
                      ? "bg-success/15 text-success"
                      : signal.includes("put")
                        ? "bg-destructive/15 text-destructive"
                        : "bg-muted/15 text-muted"
                  )}
                >
                  {(t.signal || "—").slice(0, 4)}
                </span>
                <span className="text-muted flex-1 truncate">{String(t.info || "")}</span>
                <span
                  className={cn(
                    "font-semibold mono shrink-0",
                    isWin ? "text-success" : isLoss ? "text-destructive" : "text-muted"
                  )}
                >
                  {isNaN(profit) ? "—" : `${isWin ? "+" : ""}${profit.toFixed(2)}`}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}