import * as React from "react"
import {
  Line,
  LineChart,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  CartesianGrid,
} from "recharts"
import { cn } from "@/lib/utils"

export interface EquityPoint {
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
  return (
    <div className={cn("w-full h-[320px] bg-surface border border-border rounded-lg p-4", className)}>
      <h2 className="text-sm font-medium mb-4">Curva de Equity</h2>
      {chartData.length === 0 ? (
        <div className="h-[240px] flex items-center justify-center text-muted text-sm">
          Aguardando trades para gerar o gráfico…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#232A36" />
            <XAxis dataKey="time" stroke="#8A8F98" tick={{ fontSize: 11 }} />
            <YAxis stroke="#8A8F98" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "#151A23", border: "1px solid #232A36", borderRadius: 8 }}
              labelStyle={{ color: "#E6E6E6" }}
            />
            <Legend />
            <Area type="monotone" dataKey="profit" name="Lucro" fill="#3DD68C" fillOpacity={0.15} stroke="#3DD68C" />
            <Line type="monotone" dataKey="balance" name="Saldo" stroke="#818CF8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}