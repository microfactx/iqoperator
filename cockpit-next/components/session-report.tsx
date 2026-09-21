"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface SessionReportProps {
  trades: number
  wins: number
  winrate: number
  profit: number
  balance: string
  asset?: string
  strategy?: string
  uptime?: number
  className?: string
}

function formatUptime(uptime?: number): string {
  if (uptime === undefined || uptime === null || Number.isNaN(uptime) || uptime < 0) return "—"
  const h = Math.floor(uptime / 3600)
  const m = Math.floor((uptime % 3600) / 60)
  return `${h}h ${m}m`
}

function formatWinrate(winrate: number): string {
  if (Number.isNaN(winrate)) return "0.0%"
  return `${(winrate * 100).toFixed(1)}%`
}

function formatProfit(profit: number): string {
  const sign = profit >= 0 ? "+" : "-"
  return `${sign}R$ ${Math.abs(profit).toFixed(2)}`
}

export function SessionReport({
  trades,
  wins,
  winrate,
  profit,
  balance,
  asset,
  strategy,
  uptime,
  className,
}: SessionReportProps) {
  const [copied, setCopied] = React.useState(false)
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  React.useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const summary = React.useMemo(() => {
    const strat = strategy?.trim() ? strategy : "—"
    const atv = asset?.trim() ? asset : "—"
    return [
      "IQOperator — resumo da sessão",
      `Estratégia: ${strat} | Ativo: ${atv} | Uptime: ${formatUptime(uptime)}`,
      `Trades: ${trades} (${wins} wins) | Winrate: ${formatWinrate(winrate)} | Lucro: ${formatProfit(profit)} | Saldo: ${balance}`,
    ].join("\n")
  }, [trades, wins, winrate, profit, balance, asset, strategy, uptime])

  function fallbackCopy(text: string): boolean {
    try {
      const ta = document.createElement("textarea")
      ta.value = text
      ta.setAttribute("readonly", "")
      ta.style.position = "fixed"
      ta.style.top = "-9999px"
      ta.style.opacity = "0"
      document.body.appendChild(ta)
      ta.select()
      ta.setSelectionRange(0, ta.value.length)
      const ok = document.execCommand("copy")
      document.body.removeChild(ta)
      return ok
    } catch {
      return false
    }
  }

  function showCopiedFeedback() {
    setCopied(true)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setCopied(false), 2000)
  }

  async function handleCopy() {
    try {
      if (
        typeof navigator !== "undefined" &&
        navigator.clipboard &&
        typeof navigator.clipboard.writeText === "function"
      ) {
        await navigator.clipboard.writeText(summary)
        showCopiedFeedback()
        return
      }
    } catch {
      // cai para o fallback abaixo sem quebrar
    }
    const ok = fallbackCopy(summary)
    if (ok) showCopiedFeedback()
  }

  function handleDownload() {
    const blob = new Blob([summary], { type: "text/plain;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "iqoperator-resumo-sessao.txt"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4 flex flex-col gap-3", className)}>
      <h2 className="text-sm font-medium">Resumo da Sessão</h2>

      <pre className="mono text-xs whitespace-pre-wrap bg-background/60 rounded p-3">{summary}</pre>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleCopy}
          className="text-xs px-3 py-1.5 rounded border border-border hover:opacity-80 transition-opacity"
        >
          {copied ? <span className="text-success">Copiado ✓</span> : "Copiar resumo"}
        </button>
        <button
          type="button"
          onClick={handleDownload}
          className="text-xs px-3 py-1.5 rounded border border-border text-muted hover:opacity-80 transition-opacity"
        >
          Baixar .txt
        </button>
      </div>
    </div>
  )
}
