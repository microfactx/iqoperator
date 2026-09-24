"use client"

import * as React from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"
import { ChartTooltip } from "@/components/ui/chart-tooltip"

interface StakePoint {
  trade: number
  stake: number
}

function parseStake(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null
  const n = typeof value === "number" ? value : parseFloat(String(value).replace(",", "."))
  if (!Number.isFinite(n)) return null
  return n
}

export function StakeEvolution({
  trades,
  className,
}: {
  trades: any[]
  className?: string
}) {
  const data: StakePoint[] = React.useMemo(() => {
    if (!trades || trades.length === 0) return []
    const chrono = [...trades].reverse()
    return chrono.map((t, i) => ({
      trade: i + 1,
      stake: parseStake(t?.stake) ?? 0,
    }))
  }, [trades])

  const average = React.useMemo(() => {
    if (data.length === 0) return 0
    const sum = data.reduce((acc, p) => acc + p.stake, 0)
    return sum / data.length
  }, [data])

  const current = data.length > 0 ? data[data.length - 1].stake : 0

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium">Evolução do Stake (Kelly)</h2>
        {data.length > 0 && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-surface border border-border text-muted font-mono">
            Atual {current.toFixed(2)} · Média {average.toFixed(2)}
          </span>
        )}
      </div>

      {data.length === 0 ? (
        <div className="h-[220px] flex items-center justify-center text-sm text-muted">
          Sem dados de stake ainda
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart
            data={data}
            syncId="cockpit-session"
            margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#232A36" />
            <XAxis
              dataKey="trade"
              stroke="#8A8F98"
              tick={{ fontSize: 11 }}
              label={{ value: "trade", position: "insideBottomRight", fontSize: 11, fill: "#8A8F98" }}
            />
            <YAxis
              stroke="#8A8F98"
              tick={{ fontSize: 11 }}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => Number(v).toFixed(1)}
            />
            <Tooltip
              content={
                <ChartTooltip
                  labelFormatter={(label) => `Trade #${label}`}
                  valueFormatter={(value) => `${Number(value).toFixed(2)}`}
                />
              }
            />
            <ReferenceLine
              y={average}
              stroke="#818CF8"
              strokeDasharray="5 5"
              label={{
                value: `média ${average.toFixed(2)}`,
                fontSize: 11,
                fill: "#818CF8",
                position: "insideTopRight",
              }}
            />
            <Line
              type="monotone"
              dataKey="stake"
              name="Stake"
              stroke="#F97316"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
