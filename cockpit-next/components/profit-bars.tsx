"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"
import { ChartTooltipContainer } from "@/components/ui/chart-tooltip"

const WIN_FILL = "#3DD68C"
const LOSS_FILL = "#FF5470"
const FLAT_FILL = "#8A8F98"

interface ProfitBarPoint {
  trade: number
  idx: number
  profit: number
  label: string
  time: string
  signal: string
}

function toProfit(t: any): number {
  const v = parseFloat(t?.profit)
  return isNaN(v) ? 0 : v
}

function shortTime(raw: any): string {
  if (raw === null || raw === undefined) return ""
  const s = String(raw)
  const m = s.match(/(\d{1,2}:\d{2}(?::\d{2})?)/)
  if (m) return m[1].slice(0, 5)
  return s.slice(0, 5)
}

function ProfitTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload?: ProfitBarPoint }>
  label?: string | number
}) {
  if (!active || !payload || payload.length === 0 || !payload[0]?.payload) return null
  const p = payload[0].payload
  const profit = typeof p.profit === "number" ? p.profit : 0
  const color = profit > 0 ? WIN_FILL : profit < 0 ? LOSS_FILL : FLAT_FILL

  return (
    <ChartTooltipContainer>
      <div className="flex items-center justify-between gap-3 pb-1 mb-1.5 border-b border-white/10 text-[11px] font-semibold text-foreground/90">
        <span>Trade #{p.idx}</span>
        {p.time && <span className="text-muted font-normal">{p.time}</span>}
      </div>
      {p.signal && (
        <div className="text-[11px] text-muted mb-1 flex items-center justify-between">
          <span>Sinal:</span>
          <span className="font-semibold text-foreground">{p.signal.toUpperCase()}</span>
        </div>
      )}
      <div className="flex items-center justify-between gap-4">
        <span className="text-muted">Lucro:</span>
        <span className="font-bold tabular-nums" style={{ color }}>
          {profit > 0 ? "+" : ""}{profit.toFixed(2)}
        </span>
      </div>
    </ChartTooltipContainer>
  )
}

export function ProfitBars({
  trades,
  className,
}: {
  trades: any[]
  className?: string
}) {
  const data: ProfitBarPoint[] = React.useMemo(() => {
    if (!trades || trades.length === 0) return []
    const chrono = [...trades].reverse()
    return chrono.map((t, i) => ({
      trade: i + 1,
      idx: i + 1,
      profit: toProfit(t),
      label: String(i + 1),
      time: String(t?.time ?? ""),
      signal: String(t?.signal ?? ""),
    }))
  }, [trades])

  const { sumWins, sumLosses } = React.useMemo(() => {
    let w = 0
    let l = 0
    for (const d of data) {
      if (d.profit > 0) w += d.profit
      else if (d.profit < 0) l += d.profit
    }
    return { sumWins: w, sumLosses: l }
  }, [data])

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-sm font-medium">Lucro por Trade</h2>
        {data.length > 0 && (
          <div className="flex items-center gap-3 text-xs font-mono">
            <span>
              <span className="text-muted">Ganhos: </span>
              <span className="font-semibold text-success" style={{ color: WIN_FILL }}>
                +{sumWins.toFixed(2)}
              </span>
            </span>
            <span>
              <span className="text-muted">Perdas: </span>
              <span className="font-semibold text-destructive" style={{ color: LOSS_FILL }}>
                {sumLosses.toFixed(2)}
              </span>
            </span>
          </div>
        )}
      </div>

      {data.length === 0 ? (
        <div className="h-[240px] flex items-center justify-center text-sm text-muted">
          Sem trades ainda
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart
            data={data}
            syncId="cockpit-session"
            margin={{ top: 5, right: 12, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#232A36" />
            <XAxis
              dataKey="trade"
              stroke="#8A8F98"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number, i: number) => shortTime(data[i]?.time) || String(v)}
              label={{ value: "trade", position: "insideBottomRight", fontSize: 11, fill: "#8A8F98" }}
            />
            <YAxis stroke="#8A8F98" tick={{ fontSize: 11 }} />
            <Tooltip
              content={<ProfitTooltip />}
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
            />
            <ReferenceLine y={0} stroke="#232A36" />
            <Bar dataKey="profit" name="Lucro" radius={[3, 3, 0, 0]}>
              {data.map((d, i) => (
                <Cell
                  key={`cell-${i}`}
                  fill={d.profit > 0 ? WIN_FILL : d.profit < 0 ? LOSS_FILL : FLAT_FILL}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {data.length > 0 && (
        <p className="mt-2 text-[11px] text-muted font-mono">
          {data.length} {data.length === 1 ? "trade" : "trades"} em ordem cronológica ·
          verde lucro, vermelho prejuízo
        </p>
      )}
    </div>
  )
}
