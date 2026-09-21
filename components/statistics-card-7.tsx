import * as React from "react"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Users, DollarSign, PieChart, Calendar, AlertCircle } from "lucide-react"

export interface StatisticsCard7Props {
  title: string
  value: string | number
  subtitle?: string
  metric?: "winrate" | "profit" | "trades" | "balance" | "payout"
  showTrend?: boolean
  className?: string
}

export function StatisticsCard7({
  title,
  value,
  subtitle,
  metric = "trades",
  showTrend = true,
  className,
}: StatisticsCard7Props) {
  // Determinar classe de cor e ícone baseado na métrica
  const metricMap: Record<string, { icon: React.ComponentType; textColor: string; bgColor: string }> = {
    winrate: {
      icon: TrendingUp,
      textColor: "#3dd68c",
      bgColor: "rgba(61, 214, 140, 0.15)",
    },
    profit: {
      icon: TrendingUp,
      textColor: "#3dd68c",
      bgColor: "rgba(61, 214, 140, 0.15)",
    },
    trades: {
      icon: Users,
      textColor: "#6366f1",
      bgColor: "rgba(99, 102, 241, 0.15)",
    },
    balance: {
      icon: DollarSign,
      textColor: "#f97316",
      bgColor: "rgba(249, 115, 22, 0.15)",
    },
    payout: {
      icon: AlertCircle,
      textColor: "#f472b6",
      bgColor: "rgba(244, 114, 182, 0.15)",
    },
  }

  const metricInfo = metricMap[metric] || metricMap.trades
  const valueNum = typeof value === "number" ? value : 0
  const formattedValue = typeof value === "number" 
    ? `${valueNum >= 0 ? "+" : ""}${valueNum.toFixed(2)}`
    : String(value)

  // Determinar winrate status
  const isWinrateGood = metric === "winrate" ? valueNum >= 0.5348 : null

  return (
    <div className={cn(
      "rounded-lg border border-border flex flex-col items-center py-4 bg-card hover:bg-muted/50 transition-colors",
      className,
    )}>
      <div className="w-full flex items-end justify-between pb-2">
        <span className="text-xs font-medium opacity-60">{title}</span>
        {showTrend && metricInfo.icon && (
          <metricInfo.icon
            className={cn(
              `h-4 w-4 text-${metricInfo.textColor} rotate-${isWinrateGood ? "-15" : "0"} transition-transform`,
              isWinrateGood ? "ok" : ""
            )}
          />
        )}
      </div>

      <p className={cn(
        "font-semibold line-clamp-1",
        isWinrateGood ? "ok" : "",
        `text-${metricInfo.textColor}`,
      )}>
        {formattedValue}
      </p>

      {subtitle && (
        <p className="text-xs opacity-60 mt-1 line-clamp-1">
          {subtitle}
        </p>
      )}
    </div>
  )
}