"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"

interface Bucket {
  faixa: string
  total: number
}

const BUCKETS: { label: string; min: number; max: number | null }[] = [
  { label: "0.70-0.75", min: 0.7, max: 0.75 },
  { label: "0.75-0.80", min: 0.75, max: 0.8 },
  { label: "0.80-0.85", min: 0.8, max: 0.85 },
  { label: "0.85-0.90", min: 0.85, max: 0.9 },
  { label: "0.90+", min: 0.9, max: null },
]

export function PayoutStats({
  trades,
  className,
}: {
  trades: any[]
  className?: string
}) {
  const payouts: number[] = React.useMemo(() => {
    if (!trades) return []
    return trades
      .map((t) => parseFloat(t?.payout))
      .filter((v) => !isNaN(v) && isFinite(v))
  }, [trades])

  const stats = React.useMemo(() => {
    if (payouts.length === 0) return { medio: 0, min: 0, max: 0 }
    const sum = payouts.reduce((a, b) => a + b, 0)
    return {
      medio: sum / payouts.length,
      min: Math.min(...payouts),
      max: Math.max(...payouts),
    }
  }, [payouts])

  const data: Bucket[] = React.useMemo(() => {
    return BUCKETS.map((b) => ({
      faixa: b.label,
      total:
        b.max === null
          ? payouts.filter((p) => p >= b.min).length
          : payouts.filter((p) => p >= b.min && p < b.max).length,
    }))
  }, [payouts])

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium">Distribuição de Payout</h2>
        <span className="text-[11px] text-muted">{payouts.length} trades</span>
      </div>

      {payouts.length === 0 ? (
        <div className="h-[240px] flex items-center justify-center text-sm text-muted">
          Sem trades para calcular o payout
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div className="bg-background/60 rounded px-3 py-2">
              <p className="text-[11px] text-muted">Médio</p>
              <p className="text-sm font-semibold">{stats.medio.toFixed(3)}</p>
            </div>
            <div className="bg-background/60 rounded px-3 py-2">
              <p className="text-[11px] text-muted">Mín</p>
              <p className="text-sm font-semibold">{stats.min.toFixed(3)}</p>
            </div>
            <div className="bg-background/60 rounded px-3 py-2">
              <p className="text-[11px] text-muted">Máx</p>
              <p className="text-sm font-semibold">{stats.max.toFixed(3)}</p>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#232A36" />
              <XAxis dataKey="faixa" stroke="#8A8F98" tick={{ fontSize: 11 }} />
              <YAxis stroke="#8A8F98" tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: "#151A23", border: "1px solid #232A36", borderRadius: 8 }}
                labelStyle={{ color: "#E6E6E6" }}
                formatter={(value: any) => [`${value} trades`, "Total"]}
                labelFormatter={(label: any) => `Payout ${label}`}
              />
              <Bar dataKey="total" name="Trades" fill="#818CF8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-2 text-[11px] text-muted">
            Payout médio {stats.medio.toFixed(3)} · faixa {stats.min.toFixed(2)}–{stats.max.toFixed(2)}
          </p>
        </>
      )}
    </div>
  )
}
