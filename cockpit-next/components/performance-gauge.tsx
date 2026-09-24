import * as React from "react"
import { Gauge } from "lucide-react"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { cn } from "@/lib/utils"
import { ChartTooltip } from "@/components/ui/chart-tooltip"

export function PerformanceGauge({
  wins,
  trades,
  className,
}: {
  wins: number
  trades: number
  className?: string
}) {
  const losses = Math.max(trades - wins, 0)
  const winrate = trades ? (wins / trades) * 100 : 0
  const data = [
    { name: "Vitórias", value: wins, color: "#3DD68C" },
    { name: "Derrotas", value: losses, color: "#FF5470" },
  ]
  const good = winrate >= 53.48

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4 flex flex-col", className)}>
      <div className="flex items-center gap-2 mb-2"><Gauge size={14} className="text-muted" /><h2 className="text-sm font-medium">Performance</h2></div>
      <div className="relative flex-1 min-h-[180px]">
        {trades === 0 ? (
          <div className="h-[180px] flex items-center justify-center text-muted text-sm">
            Sem trades ainda
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                innerRadius={58}
                outerRadius={80}
                paddingAngle={3}
                strokeWidth={0}
              >
                {data.map((d, i) => (
                  <Cell key={i} fill={d.color} />
                ))}
              </Pie>
              <Tooltip
                content={
                  <ChartTooltip
                    hideLabel
                    valueFormatter={(value) => `${value} trades`}
                  />
                }
              />
            </PieChart>
          </ResponsiveContainer>
        )}
        {trades > 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-3xl font-bold" style={{ color: good ? "#3DD68C" : "#FF5470" }}>
              {winrate.toFixed(1)}%
            </span>
            <span className="text-xs text-muted">winrate</span>
          </div>
        )}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center">
        <div className="bg-background/60 rounded p-2">
          <div className="text-lg font-bold" style={{ color: "#3DD68C" }}>{wins}</div>
          <div className="text-[11px] text-muted">Vitórias</div>
        </div>
        <div className="bg-background/60 rounded p-2">
          <div className="text-lg font-bold" style={{ color: "#FF5470" }}>{losses}</div>
          <div className="text-[11px] text-muted">Derrotas</div>
        </div>
      </div>
    </div>
  )
}