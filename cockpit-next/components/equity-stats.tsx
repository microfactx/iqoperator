"use client"

import * as React from "react"
import { BarChart3 } from "lucide-react"
import { cn } from "@/lib/utils"

function toNum(v: unknown): number {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? ""))
  return isNaN(n) ? NaN : n
}

function fmt(n: number | null): string {
  if (n === null || n === undefined || isNaN(n)) return "—"
  return n.toFixed(2)
}

export function EquityStats({ trades }: { trades: any[] }) {
  const rows = React.useMemo(() => (Array.isArray(trades) ? trades : []), [trades])

  const stats = React.useMemo(() => {
    const profits = rows.map((t) => toNum(t.profit)).filter((n) => !isNaN(n))
    if (profits.length === 0) return null
    const wins = profits.filter((p) => p > 0)
    const losses = profits.filter((p) => p < 0)
    const sumWins = wins.reduce((a, b) => a + b, 0)
    const sumLosses = losses.reduce((a, b) => a + b, 0)
    const total = profits.reduce((a, b) => a + b, 0)
    return {
      n: profits.length,
      profitFactor: losses.length === 0 ? null : sumWins / Math.abs(sumLosses),
      avgWin: wins.length > 0 ? sumWins / wins.length : null,
      avgLoss: losses.length > 0 ? sumLosses / losses.length : null,
      best: Math.max(...profits),
      worst: Math.min(...profits),
      expectancy: total / profits.length,
    }
  }, [rows])

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3"><BarChart3 size={14} className="text-muted" /><h2 className="text-sm font-medium">Estatísticas da Curva de Capital</h2></div>

      {stats === null ? (
        <div className="flex items-center justify-center py-8 text-sm text-muted">
          Sem dados suficientes
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="bg-background/60 rounded px-3 py-2.5">
            <p className="text-[11px] text-muted">Profit Factor</p>
            <p
              className={cn(
                "font-mono text-sm font-semibold mt-0.5",
                stats.profitFactor === null
                  ? "text-muted"
                  : stats.profitFactor > 1
                    ? "text-success"
                    : stats.profitFactor < 1
                      ? "text-destructive"
                      : "text-foreground"
              )}
            >
              {fmt(stats.profitFactor)}
            </p>
          </div>

          <div className="bg-background/60 rounded px-3 py-2.5">
            <p className="text-[11px] text-muted">Gain médio</p>
            <p
              className={cn(
                "font-mono text-sm font-semibold mt-0.5",
                stats.avgWin === null ? "text-muted" : "text-success"
              )}
            >
              {stats.avgWin === null ? "—" : `+${fmt(stats.avgWin)}`}
            </p>
          </div>

          <div className="bg-background/60 rounded px-3 py-2.5">
            <p className="text-[11px] text-muted">Loss médio</p>
            <p
              className={cn(
                "font-mono text-sm font-semibold mt-0.5",
                stats.avgLoss === null ? "text-muted" : "text-destructive"
              )}
            >
              {fmt(stats.avgLoss)}
            </p>
          </div>

          <div className="bg-background/60 rounded px-3 py-2.5">
            <p className="text-[11px] text-muted">Melhor trade</p>
            <p className="font-mono text-sm font-semibold mt-0.5 text-success">
              {stats.best > 0 ? `+${fmt(stats.best)}` : fmt(stats.best)}
            </p>
          </div>

          <div className="bg-background/60 rounded px-3 py-2.5">
            <p className="text-[11px] text-muted">Pior trade</p>
            <p className="font-mono text-sm font-semibold mt-0.5 text-destructive">
              {fmt(stats.worst)}
            </p>
          </div>

          <div className="bg-background/60 rounded px-3 py-2.5">
            <p className="text-[11px] text-muted">Expectancy / trade</p>
            <p
              className={cn(
                "font-mono text-sm font-semibold mt-0.5",
                stats.expectancy > 0
                  ? "text-success"
                  : stats.expectancy < 0
                    ? "text-destructive"
                    : "text-muted"
              )}
            >
              {stats.expectancy > 0
                ? `+${fmt(stats.expectancy)}`
                : fmt(stats.expectancy)}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
