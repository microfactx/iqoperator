"use client"

import * as React from "react"
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"
import { ChartTooltip } from "@/components/ui/chart-tooltip"

interface PayoutPoint {
  payout: number
  profit: number
}

function toNumber(value: unknown): number | null {
  const n = typeof value === "number" ? value : parseFloat(String(value ?? ""))
  return Number.isFinite(n) ? n : null
}

function isWin(profit: number): boolean {
  return profit > 0
}

export function PayoutScatter({
  trades,
  className,
}: {
  trades: any[]
  className?: string
}) {
  const { wins, losses } = React.useMemo(() => {
    const w: PayoutPoint[] = []
    const l: PayoutPoint[] = []
    if (!Array.isArray(trades)) return { wins: w, losses: l }
    for (const t of trades) {
      const payout = toNumber(t?.payout)
      const profit = toNumber(t?.profit)
      if (payout === null || profit === null) continue
      const point: PayoutPoint = { payout, profit }
      if (isWin(profit)) w.push(point)
      else l.push(point)
    }
    return { wins: w, losses: l }
  }, [trades])

  const total = wins.length + losses.length

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <h2 className="text-sm font-medium mb-3">Payout × Lucro</h2>

      {total === 0 ? (
        <div className="h-[240px] flex items-center justify-center text-sm text-muted">
          Sem dados suficientes
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <ScatterChart margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#232A36" />
            <XAxis
              type="number"
              dataKey="payout"
              name="Payout"
              stroke="#8A8F98"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v}%`}
              label={{ value: "Payout (%)", position: "insideBottomRight", fontSize: 11, fill: "#8A8F98" }}
            />
            <YAxis
              type="number"
              dataKey="profit"
              name="Lucro"
              stroke="#8A8F98"
              tick={{ fontSize: 11 }}
              label={{ value: "Lucro", angle: -90, position: "insideLeft", fontSize: 11, fill: "#8A8F98" }}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3", stroke: "#232A36" }}
              content={
                <ChartTooltip
                  labelFormatter={() => "Payout × Lucro"}
                  valueFormatter={(value, name) => {
                    const n = Number(value)
                    if (name === "Payout") return `${Number.isFinite(n) ? n.toFixed(2) : value}%`
                    return `${Number.isFinite(n) && n >= 0 ? "+" : ""}${Number.isFinite(n) ? n.toFixed(2) : value}`
                  }}
                />
              }
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Scatter name="Wins" data={wins} fill="#3DD68C" />
            <Scatter name="Losses" data={losses} fill="#FF5470" />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
