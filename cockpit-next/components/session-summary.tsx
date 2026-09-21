import * as React from "react"
import { cn } from "@/lib/utils"

export interface SessionInfo {
  last_tick?: string
  asset?: string
  balance?: number
  balance_type?: string
  strategy?: string
  profit_session?: number
}

export function SessionSummary({
  bot,
  uptime,
  stopWin = 50,
  stopLoss = 30,
  className,
}: {
  bot: SessionInfo | null
  uptime?: number
  stopWin?: number
  stopLoss?: number
  className?: string
}) {
  const session = bot?.profit_session ?? 0
  const isNegative = session < 0
  const pct = isNegative
    ? Math.min(Math.abs(session) / stopLoss, 1) * 100
    : Math.min(session / stopWin, 1) * 100

  const barColor = isNegative ? "#FF5470" : "#3DD68C"
  const uptimeStr = uptime
    ? `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`
    : "—"

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4 flex flex-col gap-3", className)}>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium">Sessão</h2>
        <span className="text-[11px] px-2 py-0.5 rounded-full border border-border text-muted mono">
          up {uptimeStr}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="bg-background/60 rounded p-2">
          <div className="text-muted mb-1">Estratégia</div>
          <div className="font-semibold mono">{bot?.strategy || "—"}</div>
        </div>
        <div className="bg-background/60 rounded p-2">
          <div className="text-muted mb-1">Ativo</div>
          <div className="font-semibold mono">{bot?.asset || "—"}</div>
        </div>
        <div className="bg-background/60 rounded p-2">
          <div className="text-muted mb-1">Conta</div>
          <div className="font-semibold mono">{bot?.balance_type || "—"}</div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-muted">Lucro da sessão</span>
          <span className="font-semibold" style={{ color: session >= 0 ? "#3DD68C" : "#FF5470" }}>
            {session >= 0 ? "+" : ""}
            {session.toFixed(2)}
          </span>
        </div>
        <div className="h-2.5 w-full bg-background rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: barColor }}
          />
        </div>
        <div className="flex justify-between text-[11px] text-muted mt-1 mono">
          <span>stop-loss −{stopLoss}</span>
          <span>0</span>
          <span>stop-win +{stopWin}</span>
        </div>
      </div>

      {bot?.balance !== undefined && (
        <div className="flex items-center justify-between text-xs border-t border-border pt-2">
          <span className="text-muted">Saldo na última atualização</span>
          <span className="font-semibold mono">{bot.balance}</span>
        </div>
      )}
    </div>
  )
}