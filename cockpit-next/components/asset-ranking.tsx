"use client";

import { Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

export type AssetStat = {
  asset: string;
  trades: number;
  wins: number;
  winrate: number;
  profit: number;
};

export function AssetRanking({ byAsset }: { byAsset: AssetStat[] }) {
  const rows = Array.isArray(byAsset) ? byAsset : [];
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Trophy size={14} className="text-muted" />
        <h3 className="text-sm font-medium">Ranking por Ativo</h3>
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-muted">Sem trades ainda.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted uppercase tracking-wide text-[11px]">
                <th className="text-left font-medium pb-2">Ativo</th>
                <th className="text-right font-medium pb-2">Trades</th>
                <th className="text-right font-medium pb-2">Winrate</th>
                <th className="text-right font-medium pb-2">Lucro</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.asset} className="border-t border-border">
                  <td className="py-2 font-mono whitespace-nowrap">
                    {i === 0 ? "🥇 " : ""}{r.asset}
                  </td>
                  <td className="py-2 font-mono text-right">{r.trades}</td>
                  <td className={cn(
                    "py-2 font-mono text-right",
                    r.winrate >= 0.5348 ? "text-success" : "text-destructive"
                  )}>
                    {(r.winrate * 100).toFixed(1)}%
                  </td>
                  <td className={cn(
                    "py-2 font-mono text-right font-semibold",
                    r.profit >= 0 ? "text-success" : "text-destructive"
                  )}>
                    {r.profit >= 0 ? "+" : ""}{r.profit.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
