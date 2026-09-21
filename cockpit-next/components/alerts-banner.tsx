"use client"

import * as React from "react"
import { BellRing } from "lucide-react"
import { cn } from "@/lib/utils"

export interface AlertTrade {
  time: string
  signal: string
  info: string
  payout: string
  winrate: string
  kelly: string
  stake: string
  profit: string
  balance: string
}

interface AlertsBannerProps {
  trades: AlertTrade[]
  winrate: number
  alive: boolean
  className?: string
}

const WINRATE_META = 0.5348
const PAYOUT_MINIMO = 0.8

interface AlertItem {
  key: string
  color: string
  text: string
}

export function AlertsBanner({ trades, winrate, alive, className }: AlertsBannerProps) {
  const alerts: AlertItem[] = React.useMemo(() => {
    const items: AlertItem[] = []
    const total = Array.isArray(trades) ? trades.length : 0

    // Sem trades: só aviso cinza (mais vermelho se bot parado)
    if (total === 0) {
      if (!alive) {
        items.push({
          key: "stopped",
          color: "#FF5470",
          text: "Bot sem heartbeat — verifique o worker",
        })
      }
      items.push({
        key: "empty",
        color: "#8A8F98",
        text: "Nenhuma trade registrada ainda",
      })
      return items
    }

    // Bot parado
    if (!alive) {
      items.push({
        key: "stopped",
        color: "#FF5470",
        text: "Bot sem heartbeat — verifique o worker",
      })
    }

    // Winrate abaixo da meta
    if (Number.isFinite(winrate) && winrate < WINRATE_META) {
      const pct = (winrate * 100).toFixed(1)
      items.push({
        key: "winrate",
        color: "#FACC15",
        text: `Winrate ${pct}% abaixo da meta 53.5%`,
      })
    }

    // Payout médio abaixo do mínimo
    const payouts = trades
      .map((t) => parseFloat(t.payout))
      .filter((v) => Number.isFinite(v))
    if (payouts.length > 0) {
      const media = payouts.reduce((acc, v) => acc + v, 0) / payouts.length
      if (media < PAYOUT_MINIMO) {
        items.push({
          key: "payout",
          color: "#FACC15",
          text: `Payout médio ${media.toFixed(2)} abaixo do mínimo 0.80`,
        })
      }
    }

    // Tudo ok
    if (items.length === 0) {
      items.push({
        key: "ok",
        color: "#3DD68C",
        text: "Tudo dentro dos parâmetros ✓",
      })
    }

    return items
  }, [trades, winrate, alive])

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <div className="flex items-center gap-2 mb-3"><BellRing size={14} className="text-muted" /><h2 className="text-sm font-medium">Alertas</h2></div>
      <div className="flex flex-col gap-2">
        {alerts.map((alert) => (
          <div key={alert.key} className="flex items-center gap-2 text-xs">
            <span
              className="inline-block h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: alert.color }}
            />
            <span>{alert.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
