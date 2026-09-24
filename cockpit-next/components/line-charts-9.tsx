"use client"

import * as React from "react"
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { cn } from "@/lib/utils"
import { ChartTooltip } from "@/components/ui/chart-tooltip"

export interface EquityPoint {
  trade?: number
  time: string
  profit: number
  balance: number
}

export function EquityCurveChart({
  data: chartData,
  className,
}: {
  data: EquityPoint[]
  className?: string
}) {
  const data = React.useMemo(() => {
    return chartData.map((d, i) => ({
      ...d,
      trade: d.trade ?? i + 1,
    }))
  }, [chartData])

  return (
    <div className={cn("w-full h-[320px] bg-surface border border-border rounded-lg p-4", className)}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium">Curva de Equity</h2>
        {data.length > 0 && (
          <span className="text-[11px] font-mono text-muted">
            {data.length} {data.length === 1 ? "trade sincronizado" : "trades sincronizados"}
          </span>
        )}
      </div>

      {data.length === 0 ? (
        <div className="h-[240px] flex items-center justify-center text-muted text-sm">
          Aguardando trades para gerar o gráfico…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart
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
            <YAxis stroke="#8A8F98" tick={{ fontSize: 11 }} />
            <Tooltip
              content={
                <ChartTooltip
                  labelFormatter={(label, p) => {
                    const itemTime = p?.[0]?.payload?.time
                    return itemTime ? `Trade #${label} · ${itemTime}` : `Trade #${label}`
                  }}
                  valueFormatter={(val, name) => {
                    const num = Number(val)
                    if (name === "Lucro") {
                      return `${num >= 0 ? "+" : ""}${num.toFixed(2)}`
                    }
                    return num.toFixed(2)
                  }}
                />
              }
            />
            <Legend
              wrapperStyle={{ fontSize: "11px", paddingTop: "4px" }}
              formatter={(value) => <span className="text-muted font-mono">{value}</span>}
            />
            <Area
              type="monotone"
              dataKey="profit"
              name="Lucro"
              fill="#3DD68C"
              fillOpacity={0.15}
              stroke="#3DD68C"
            />
            <Line
              type="monotone"
              dataKey="balance"
              name="Saldo"
              stroke="#818CF8"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}