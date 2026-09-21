import * as React from "react"
import { ArrowLeftRight, TrendingUp, Trophy, Wallet } from "lucide-react"
import { cn } from "@/lib/utils"
import { NumberTicker } from "@/components/brand/number-ticker"

export interface StatisticsCard7Props {
  title: string
  value: string | number
  subtitle?: string
  metric?: "winrate" | "profit" | "trades" | "balance" | "payout"
  className?: string
}

const METRIC_COLORS: Record<string, string> = {
  winrate: "#3DD68C",
  profit: "#3DD68C",
  trades: "#818CF8",
  balance: "#F97316",
  payout: "#F472B6",
}

const METRIC_ICONS: Record<string, typeof Trophy> = {
  winrate: Trophy,
  profit: TrendingUp,
  trades: ArrowLeftRight,
  balance: Wallet,
  payout: Wallet,
}

export function StatisticsCard7({
  title,
  value,
  subtitle,
  metric = "trades",
  className,
}: StatisticsCard7Props) {
  const color = METRIC_COLORS[metric] || METRIC_COLORS.trades
  const valueNum = typeof value === "number" ? value : parseFloat(String(value).replace(",", "."))
  const numeric = !isNaN(valueNum)
  const ticker =
    metric === "winrate" && numeric ? (
      <NumberTicker value={valueNum * 100} decimals={1} suffix="%" />
    ) : numeric ? (
      <NumberTicker
        value={valueNum}
        decimals={2}
        prefix={valueNum >= 0 && metric === "profit" ? "+" : ""}
      />
    ) : null

  const isGood = metric === "winrate" ? valueNum >= 0.5348 : metric === "profit" ? valueNum >= 0 : true
  const dotColor = isGood ? "#3DD68C" : "#FF5470"
  const Icon = METRIC_ICONS[metric] || METRIC_ICONS.trades

  return (
    <div
      className={cn(
        "rounded-lg border border-border flex flex-col items-center py-4 bg-surface hover:bg-muted/20 transition-colors",
        className
      )}
    >
      <div className="w-full flex items-center justify-between px-4 pb-2">
        <span className="flex items-center gap-2 text-xs font-medium text-muted"><Icon size={14} className="text-muted" />{title}</span>
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: dotColor, boxShadow: `0 0 8px ${dotColor}` }}
        />
      </div>
      <p className="font-semibold text-2xl line-clamp-1 tabular-nums" style={{ color }}>
        {ticker ?? String(value)}
      </p>
      {subtitle && <p className="text-xs text-muted mt-1 line-clamp-1">{subtitle}</p>}
    </div>
  )
}