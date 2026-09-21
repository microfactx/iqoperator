"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface BotHealth {
  last_tick?: string
  asset?: string
  balance?: number
  balance_type?: string
  strategy?: string
}

const ALIVE_THRESHOLD_S = 45

function formatUptime(uptime?: number): string {
  if (uptime === undefined || uptime === null || isNaN(uptime)) return "—"
  const h = Math.floor(uptime / 3600)
  const m = Math.floor((uptime % 3600) / 60)
  return `${h}h ${m}m`
}

export function BotHealthCard({
  bot,
  uptime,
  className,
}: {
  bot: BotHealth | null
  uptime?: number
  className?: string
}) {
  const tickDate = bot?.last_tick ? new Date(bot.last_tick) : null
  const tickValid = tickDate !== null && !isNaN(tickDate.getTime())
  const secondsAgo = tickValid ? Math.max(0, Math.floor((Date.now() - tickDate!.getTime()) / 1000)) : null
  const alive = secondsAgo !== null && secondsAgo < ALIVE_THRESHOLD_S

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium">Saúde do Bot</h2>
        {bot !== null && tickValid && (
          <span
            className={cn(
              "flex items-center gap-1.5 text-xs font-semibold",
              alive ? "text-success" : "text-destructive"
            )}
          >
            <span
              className={cn("inline-block h-2 w-2 rounded-full", alive && "animate-pulse")}
              style={{ backgroundColor: alive ? "#3DD68C" : "#FF5470" }}
            />
            {alive ? "vivo" : "parado"}
          </span>
        )}
      </div>

      {bot === null ? (
        <div className="text-sm text-muted">aguardando primeiro heartbeat…</div>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Último tick</div>
              <div className="font-semibold mono">
                {tickValid
                  ? tickDate!.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
                  : "—"}
              </div>
              <div className="text-muted mono text-[11px] mt-0.5">
                {secondsAgo === null ? "sem tick" : `há ${secondsAgo}s`}
              </div>
            </div>
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Uptime</div>
              <div className="font-semibold mono">{formatUptime(uptime)}</div>
              <div className="text-muted mono text-[11px] mt-0.5">servidor</div>
            </div>
          </div>

          <div className="border-t border-border pt-3 text-xs flex flex-col gap-1.5">
            <div className="flex justify-between">
              <span className="text-muted">Ativo</span>
              <span className="font-semibold mono">{bot.asset || "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Estratégia</span>
              <span className="font-semibold mono">{bot.strategy || "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Conta</span>
              <span className="font-semibold mono">
                {bot.balance_type || "—"}
                {bot.balance !== undefined && bot.balance !== null ? ` · ${bot.balance}` : ""}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
