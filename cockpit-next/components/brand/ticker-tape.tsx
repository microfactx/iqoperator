"use client"
import * as React from "react"
import { cn } from "@/lib/utils"

// Ticker tape (Magic UI Marquee + Kibo Ticker, MIT — port CSS puro)
// Uso: <TickerTape items={[{symbol, price, chg}]} />
export interface TickerItem {
  symbol: string
  price: string
  chg?: number // % com sinal
}

export function TickerTape({ items, className }: { items: TickerItem[]; className?: string }) {
  const row = items.length > 0 ? items : [{ symbol: "—", price: "aguardando feed", chg: 0 }]
  const loop = [...row, ...row]
  return (
    <div
      className={cn(
        "relative overflow-hidden border-y border-border bg-background/70 backdrop-blur",
        className
      )}
    >
      <div className="animate-marquee flex w-max items-center gap-8 px-4 py-2 [animation-duration:36s] hover:[animation-play-state:paused]">
        {loop.map((t, i) => (
          <span key={i} className="flex items-center gap-2 text-xs whitespace-nowrap">
            <span className="font-bold text-foreground mono">{t.symbol}</span>
            <span className="text-muted mono">{t.price}</span>
            {t.chg !== undefined && t.chg !== 0 && (
              <span className={cn("font-semibold mono", t.chg >= 0 ? "text-success" : "text-destructive")}>
                {t.chg >= 0 ? "▲" : "▼"} {Math.abs(t.chg).toFixed(2)}%
              </span>
            )}
          </span>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-[#0B0E14] to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-[#0B0E14] to-transparent" />
    </div>
  )
}