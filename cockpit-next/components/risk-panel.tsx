import * as React from "react"
import { ShieldAlert } from "lucide-react"
import { cn } from "@/lib/utils"

export function RiskPanel({
  last,
  balance,
  className,
}: {
  last: any[]
  balance: string | number
  className?: string
}) {
  const t = last && last.length > 0 ? last[0] : null
  const balNum = balance === "n/a" || balance === undefined ? NaN : parseFloat(String(balance))

  const stake = t ? parseFloat(t.stake) : NaN
  const payout = t ? parseFloat(t.payout) : NaN
  const kelly = t ? parseFloat(t.kelly) : NaN
  const kellyPct = isNaN(kelly) ? null : (kelly * 100).toFixed(1)
  const riskPct = !isNaN(stake) && !isNaN(balNum) && balNum > 0 ? (stake / balNum) * 100 : null
  const breakeven = !isNaN(payout) ? ((1 / (1 + payout)) * 100).toFixed(1) : null
  const edgePct = t && !isNaN(parseFloat(t.winrate)) && !isNaN(payout)
    ? (parseFloat(t.winrate) * 100 - (1 / (1 + payout)) * 100).toFixed(1)
    : null

  return (
    <div className={cn("bg-surface border border-border rounded-lg p-4", className)}>
      <div className="flex items-center gap-2 mb-3"><ShieldAlert size={14} className="text-muted" /><h2 className="text-sm font-medium">Gerenciamento de Risco</h2></div>

      {!t ? (
        <div className="text-sm text-muted">Sem dados de stake ainda — aguardando a primeira trade.</div>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 text-center text-xs">
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Stake (última)</div>
              <div className="font-bold mono text-base">{isNaN(stake) ? "—" : stake.toFixed(2)}</div>
            </div>
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Payout</div>
              <div className="font-bold mono text-base">
                {isNaN(payout) ? "—" : `${(payout * 100).toFixed(0)}%`}
              </div>
            </div>
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">Kelly</div>
              <div className="font-bold mono text-base">{kellyPct === null ? "—" : `${kellyPct}%`}</div>
            </div>
            <div className="bg-background/60 rounded p-2">
              <div className="text-muted mb-1">% da banca</div>
              <div className="font-bold mono text-base">
                {riskPct === null ? "—" : `${riskPct.toFixed(2)}%`}
              </div>
            </div>
          </div>

          <div className="border-t border-border pt-3 text-xs flex flex-col gap-1.5">
            <div className="flex justify-between">
              <span className="text-muted">Break-even (payout {isNaN(payout) ? "—" : `${(payout * 100).toFixed(0)}%`})</span>
              <span className="font-semibold mono">{breakeven ?? "—"}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Winrate atual</span>
              <span className="font-semibold mono">
                {t.winrate ? `${(parseFloat(t.winrate) * 100).toFixed(1)}%` : "—"}
              </span>
            </div>
            {edgePct !== null && (
              <div className="flex justify-between">
                <span className="text-muted">Edge (winrate − break-even)</span>
                <span className={cn("font-semibold mono", parseFloat(edgePct) >= 0 ? "text-success" : "text-destructive")}>
                  {parseFloat(edgePct) >= 0 ? "+" : ""}
                  {edgePct}%
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}