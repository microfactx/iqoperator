"use client"

import * as React from "react"
import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts"
import { cn } from "@/lib/utils"

interface EquityPoint {
  i: number
  equity: number
}

function toNum(v: unknown): number {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? ""))
  return isNaN(n) ? 0 : n
}

export function DrawdownCard({ trades, className }: { trades: any[]; className?: string }) {
  const { points, peak, maxDD, maxDDPct, currentDD, currentDDPct } = React.useMemo(() => {
    const chrono = [...(trades ?? [])].reverse()
    let acc = 0
    const pts: EquityPoint[] = []
    let runningPeak = 0
    let maxDrawdown = 0
    let peakAtMaxDD = 0

    chrono.forEach((t, idx) => {
      acc += toNum(t?.profit)
      pts.push({ i: idx + 1, equity: Math.round(acc * 100) / 100 })
      if (acc > runningPeak) runningPeak = acc
      const dd = runningPeak - acc
      if (dd > maxDrawdown) {
        maxDrawdown = dd
        peakAtMaxDD = runningPeak
      }
    })

    const peak = pts.length > 0 ? Math.max(0, ...pts.map((p) => p.equity)) : 0
    const lastEquity = pts.length > 0 ? pts[pts.length - 1].equity : 0
    const currentDrawdown = Math.max(0, peak - lastEquity)
    const maxPct = peakAtMaxDD > 0 ? (maxDrawdown / peakAtMaxDD) * 100 : 0
    const curPct = peak > 0 ? (currentDrawdown / peak) * 100 : 0

    return {
      points: pts,
      peak,
      maxDD: maxDrawdown,
      maxDDPct: maxPct,
      currentDD: currentDrawdown,
      currentDDPct: curPct,
    }
  }, [trades])

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <h2 className="text-sm font-medium mb-3">Drawdown</h2>

      {!trades || trades.length === 0 ? (
        <div className="text-sm text-muted">Sem trades ainda — drawdown indisponível.</div>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="h-[120px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <YAxis hide domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#151A23",
                    border: "1px solid #232A36",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelFormatter={(v) => `Trade #${v}`}
                  formatter={(value) => [`${Number(value).toFixed(2)}`, "Equity acum."]}
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="#818CF8"
                  strokeWidth={2}
                  fill="#818CF8"
                  fillOpacity={0.15}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Drawdown máx</div>
              <div className="font-bold mono text-base text-destructive">
                −{maxDD.toFixed(2)}
              </div>
              <div className="text-muted mono text-[11px] mt-0.5">{maxDDPct.toFixed(1)}%</div>
            </div>
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Drawdown atual</div>
              <div className="font-bold mono text-base">{currentDD.toFixed(2)}</div>
              <div className="text-muted mono text-[11px] mt-0.5">{currentDDPct.toFixed(1)}%</div>
            </div>
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Pico</div>
              <div className="font-bold mono text-base text-success">+{peak.toFixed(2)}</div>
              <div className="text-muted mono text-[11px] mt-0.5">equity máx</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
