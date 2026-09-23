"use client"

import * as React from "react"
import { Download, History, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  Table,
  TableHeader,
  TableHeaderRow,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table"

export interface TradeItem {
  time: string
  asset?: string
  signal: string
  info: string
  payout: string
  winrate: string
  kelly: string
  stake: string
  profit: string
  balance: string
  [key: string]: any
}

type ResultFilter = "all" | "win" | "loss"

const PAGE_SIZE = 10

function isWin(t: TradeItem): boolean {
  const p = parseFloat(t.profit)
  return !isNaN(p) && p > 0
}

function isLoss(t: TradeItem): boolean {
  const p = parseFloat(t.profit)
  return !isNaN(p) && p < 0
}

function toCSVCell(v: unknown): string {
  const s = String(v ?? "")
  return `"${s.replace(/"/g, '""')}"`
}

export function TradesHistoryFull({ trades }: { trades: any[] }) {
  const [search, setSearch] = React.useState("")
  const [filter, setFilter] = React.useState<ResultFilter>("all")
  const [assetFilter, setAssetFilter] = React.useState<string>("all")
  const [page, setPage] = React.useState(1)

  const rows = React.useMemo(() => (Array.isArray(trades) ? trades : []), [trades])

  const assetOptions = React.useMemo(() => {
    const s = new Set<string>()
    for (const t of rows) if (t.asset) s.add(String(t.asset))
    return [...s].sort()
  }, [rows])

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase()
    return rows.filter((t) => {
      if (filter === "win" && !isWin(t)) return false
      if (filter === "loss" && !isLoss(t)) return false
      if (assetFilter !== "all" && String(t.asset || "") !== assetFilter) return false
      if (!q) return true
      const hay = `${t.asset ?? ""} ${t.signal ?? ""} ${t.info ?? ""} ${t.time ?? ""}`.toLowerCase()
      return hay.includes(q)
    })
  }, [rows, search, filter, assetFilter])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const safePage = Math.min(Math.max(1, page), totalPages)
  const paged = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSearch(e.target.value)
    setPage(1)
  }

  function handleFilterChange(f: ResultFilter) {
    setFilter(f)
    setPage(1)
  }

  function handleExportCSV() {
    const header = ["Hora", "Ativo", "Sinal", "Info", "Stake", "Payout (%)", "Lucro", "Saldo"]
    const lines = filtered.map((t) =>
      [
        toCSVCell(t.time ?? ""),
        toCSVCell(t.asset ?? ""),
        toCSVCell(t.signal ?? ""),
        toCSVCell(t.info ?? ""),
        toCSVCell(t.stake ?? ""),
        toCSVCell(t.payout ?? ""),
        toCSVCell(t.profit ?? ""),
        toCSVCell(t.balance ?? ""),
      ].join(";")
    )
    const csv = [header.map(toCSVCell).join(";"), ...lines].join("\r\n")
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "trades.csv"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const filterBtn = (value: ResultFilter, label: string) => (
    <button
      key={value}
      type="button"
      onClick={() => handleFilterChange(value)}
      className={cn(
        "px-3 py-1.5 rounded text-xs font-medium border transition-colors",
        filter === value
          ? "bg-accent/15 text-accent border-accent/30"
          : "bg-background/60 text-muted border-border hover:text-foreground"
      )}
    >
      {label}
    </button>
  )

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2"><History size={14} className="text-muted" /><h2 className="text-sm font-medium">Histórico de Trades</h2></div>
        <button
          type="button"
          onClick={handleExportCSV}
          className="px-3 py-1.5 rounded text-xs font-medium border border-border bg-background/60 text-foreground hover:bg-muted/20 transition-colors inline-flex items-center gap-1.5"
        >
          <Download size={13} />Exportar CSV
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
          <input
          type="text"
          value={search}
          onChange={handleSearchChange}
          placeholder="Buscar por sinal, info ou hora..."
          className="w-full pl-9 pr-3 py-1.5 rounded text-xs bg-background/60 border border-border text-foreground placeholder:text-muted focus:outline-none focus:border-accent/50"
        />
        </div>
        <div className="flex items-center gap-2">
          {filterBtn("all", "Todas")}
          {filterBtn("win", "Wins")}
          {filterBtn("loss", "Losses")}
        </div>
        {assetOptions.length > 0 && (
          <select
            value={assetFilter}
            onChange={(e) => { setAssetFilter(e.target.value); setPage(1) }}
            className="px-3 py-1.5 rounded text-xs bg-background/60 border border-border text-foreground focus:outline-none focus:border-accent/50"
          >
            <option value="all">Todos os ativos</option>
            {assetOptions.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        )}
      </div>

      {filtered.length === 0 ? (
        <div className="flex items-center justify-center py-8 text-sm text-muted">
          Nenhuma trade encontrada
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableHeaderRow>
                  <TableCell className="text-[11px] uppercase tracking-wide text-muted font-medium">
                    Hora
                  </TableCell>
                  <TableCell className="text-[11px] uppercase tracking-wide text-muted font-medium">
                    Ativo
                  </TableCell>
                  <TableCell className="text-[11px] uppercase tracking-wide text-muted font-medium">
                    Sinal
                  </TableCell>
                  <TableCell className="text-[11px] uppercase tracking-wide text-muted font-medium text-right">
                    Stake
                  </TableCell>
                  <TableCell className="text-[11px] uppercase tracking-wide text-muted font-medium text-right">
                    Payout (%)
                  </TableCell>
                  <TableCell className="text-[11px] uppercase tracking-wide text-muted font-medium text-right">
                    Lucro
                  </TableCell>
                  <TableCell className="text-[11px] uppercase tracking-wide text-muted font-medium text-right">
                    Saldo
                  </TableCell>
                </TableHeaderRow>
              </TableHeader>
              <TableBody>
                {paged.map((t, i) => {
                  const profit = parseFloat(t.profit)
                  const win = !isNaN(profit) && profit > 0
                  const loss = !isNaN(profit) && profit < 0
                  const signal = String(t.signal || "").toLowerCase()
                  const stake = parseFloat(t.stake)
                  const payout = parseFloat(t.payout)
                  const balance = parseFloat(t.balance)
                  return (
                    <TableRow key={`${t.time}-${i}`}>
                      <TableCell className="font-mono text-xs whitespace-nowrap">
                        {String(t.time || "—")}
                      </TableCell>
                      <TableCell className="font-mono text-xs whitespace-nowrap">
                        {String(t.asset || "—")}
                      </TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "px-1.5 py-0.5 rounded text-[11px] font-bold uppercase",
                            signal.includes("call")
                              ? "bg-success/15 text-success"
                              : signal.includes("put")
                                ? "bg-destructive/15 text-destructive"
                                : "bg-muted/15 text-muted"
                          )}
                        >
                          {String(t.signal || "—")}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-right">
                        {isNaN(stake) ? "—" : stake.toFixed(2)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-right">
                        {isNaN(payout) ? "—" : payout.toFixed(2)}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "font-mono text-xs text-right font-semibold",
                          win
                            ? "text-success"
                            : loss
                              ? "text-destructive"
                              : "text-muted"
                        )}
                      >
                        {isNaN(profit)
                          ? "—"
                          : `${win ? "+" : ""}${profit.toFixed(2)}`}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-right">
                        {isNaN(balance) ? "—" : balance.toFixed(2)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>

          <div className="flex items-center justify-between mt-3">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              className="px-3 py-1.5 rounded text-xs font-medium border border-border bg-background/60 text-foreground disabled:opacity-40 disabled:cursor-not-allowed hover:bg-muted/20 transition-colors"
            >
              Anterior
            </button>
            <span className="text-xs text-muted font-mono">
              página {safePage} de {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              className="px-3 py-1.5 rounded text-xs font-medium border border-border bg-background/60 text-foreground disabled:opacity-40 disabled:cursor-not-allowed hover:bg-muted/20 transition-colors"
            >
              Próxima
            </button>
          </div>
        </>
      )}
    </div>
  )
}
