import * as React from "react"
import { Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { cn } from "@/lib/utils"

export interface LineChartPoint {
  name: string
  uv: number
  pv: number
  amt: number
}

export interface LineCharts9Props {
  data: LineChartPoint[]
  className?: string
  width?: number
  height?: number
}

export function LineCharts9({
  data,
  className,
  width = 800,
  height = 400,
}: LineCharts9Props) {
  const chartData = data.map(d => ({
    name: d.name,
    score: Math.random() * 100, // placeholder - substituir por dados reais
  }))

  return (
    <div className={cn("w-full h-[400px]", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <XAxis dataKey="name" strokeDasharray="3 3" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="score" stroke="#8884d8" fill="#8884d8" />
          <CartesianGrid strokeDasharray="3 3" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/* 
 * Versão otimizada para cockpit - usando dados do backend Python
 * Substitua a função getChartData() pela busca ao seu API
 */

interface CocktailChartData {
  time: string
  profit: number
  balance: number
}

/**
 * Componente de linha para mostrar curva de equity
 * Dados vêm do props.data ou buscados via API
 */
export function EquityCurveChart({ data: chartData }: { data: CocktailChartData[] }) {
  return (
    <ResponsiveContainer width="100%" height="400">
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
        <XAxis dataKey="time" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Area type="monotone" dataKey="profit" fill="#8884d8" fillOpacity={0.6} />
        <Line type="monotone" dataKey="profit" stroke="#8884d8" />
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="time"
          ticks={(tickValue: any) => {
            const date = new Date(tickValue)
            return date.toLocaleDateString("en-US", { month: "short" })
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}