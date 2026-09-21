"use client";

import { Workflow } from "lucide-react";
import { cn } from "@/lib/utils";

type StrategyConfigProps = {
  bot: { strategy?: string; asset?: string; balance_type?: string } | null;
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-xs text-muted">{label}</span>
      <span className="font-mono text-xs text-foreground text-right">{value}</span>
    </div>
  );
}

export function StrategyConfig({ bot }: StrategyConfigProps) {
  const strategy = bot?.strategy?.trim() ? bot.strategy : "donchian_fade";
  const asset = bot?.asset?.trim() ? bot.asset : "BTCUSD";
  const account = bot?.balance_type?.trim() ? bot.balance_type : "PRACTICE";

  const rows: Array<{ label: string; value: string }> = [
    { label: "Estratégia", value: strategy },
    { label: "Ativo", value: asset },
    { label: "Conta", value: account },
    { label: "Timeframe", value: "M15" },
    { label: "Expiração", value: "15 min" },
    { label: "Payout mínimo", value: "≥ 0.80" },
    { label: "Kelly", value: "quarter 0.25 · teto 2%" },
    { label: "Stop-win", value: "+50" },
    { label: "Stop-loss", value: "−30" },
    { label: "Martingale", value: "desligado" },
  ];

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-2"><Workflow size={14} className="text-muted" /><h3 className="text-sm font-medium">Configuração da Estratégia</h3></div>
      <dl className={cn("mt-2 divide-y divide-border")}>
        {rows.map((row) => (
          <Row key={row.label} label={row.label} value={row.value} />
        ))}
      </dl>
    </div>
  );
}
