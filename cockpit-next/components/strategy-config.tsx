"use client";

import { Workflow } from "lucide-react";
import { cn } from "@/lib/utils";

type StrategyConfigProps = {
  bot: { strategy?: string; asset?: string; balance_type?: string; ml_filter_status?: string; win_target?: number; loss_target?: number; is_compound?: boolean } | null;
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
  const mlFilter = bot?.ml_filter_status?.trim() ? bot.ml_filter_status : "OFF";
  const asset = bot?.asset?.trim() ? bot.asset : "BTCUSD";
  const account = bot?.balance_type?.trim() ? bot.balance_type : "PRACTICE";

  const winTarget = bot?.win_target ? "+" + bot.win_target : "+50";
  const lossTarget = bot?.loss_target ? "-" + bot.loss_target : "-30";
  const targetLabel = bot?.is_compound ? "(Juros Compostos)" : "";

  const rows: Array<{ label: string; value: string }> = [
    { label: "Estratégia", value: strategy },
    { label: "Filtro Preditivo ML", value: mlFilter },
    { label: "Ativo", value: asset },
    { label: "Conta", value: account },
    { label: "Timeframe", value: "M15" },
    { label: "Expiração", value: "15 min" },
    { label: "Payout mínimo", value: "≥ 0.80" },
    { label: "Kelly", value: "quarter 0.25 · teto 2%" },
    { label: "Stop-win " + targetLabel, value: winTarget },
    { label: "Stop-loss " + targetLabel, value: lossTarget },
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
