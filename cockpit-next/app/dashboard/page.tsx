"use client";
import { StatisticsCard7 } from "@/components/statistics-card-7";
import { EquityCurveChart } from "@/components/line-charts-9";
import { PerformanceGauge } from "@/components/performance-gauge";
import { SessionSummary } from "@/components/session-summary";
import { RiskPanel } from "@/components/risk-panel";
import { TradesFeed } from "@/components/trades-feed";
import { WinrateTrend } from "@/components/winrate-trend";
import { PayoutStats } from "@/components/payout-stats";
import { TradeTicket } from "@/components/trade-ticket";
import { AssetRanking } from "@/components/asset-ranking";
import { StrategyConfig } from "@/components/strategy-config";
import { DrawdownCard } from "@/components/drawdown-card";
import { BotHealthCard } from "@/components/bot-health-card";
import { TradesHistoryFull } from "@/components/trades-history-full";
import { EquityStats } from "@/components/equity-stats";
import { SignalDistribution } from "@/components/signal-distribution";
import { ProfitBars } from "@/components/profit-bars";
import { StreakTracker } from "@/components/streak-tracker";
import { StakeEvolution } from "@/components/stake-evolution";
import { GoalRing } from "@/components/goal-ring";
import { AlertsBanner } from "@/components/alerts-banner";
import { SessionReport } from "@/components/session-report";
import { PayoutScatter } from "@/components/payout-scatter";
import { Brand } from "@/components/brand/logo";
import { StatusPill } from "@/components/brand/status-pill";
import { SessionClock } from "@/components/brand/session-clock";
import { TickerTape } from "@/components/brand/ticker-tape";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { CommandMenu, CommandMenuHint } from "@/components/shell/command-menu";
import { useEffect, useState } from "react";

type S = {
  trades: number;
  wins: number;
  winrate: number;
  profit: number;
  balance: string;
  byAsset: { asset: string; trades: number; wins: number; winrate: number; profit: number }[];
  last: any[];
};

type B = {
  last_tick: string;
  asset: string;
  balance: number;
  balance_type: string;
  strategy: string;
  profit_session: number;
} | null;

export default function Dashboard() {
  const [s, setS] = useState<S>({
    trades: 0,
    wins: 0,
    winrate: 0,
    profit: 0,
    balance: "n/a",
    byAsset: [],
    last: [],
  });

  const [b, setB] = useState<B>(null);
  const [uptime, setUptime] = useState(0);
  const [msg, setMsg] = useState<string | null>(null);

  async function manual(sig: string) {
    if (!confirm(`Enviar sinal manual ${sig}?`)) return;
    setMsg("enviando...");
    try {
      const r = await fetch("/api/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ signal: sig }),
      })
        .then((x) => x.json())
        .catch(() => null);
      setMsg(r?.error ? String(r.error) : `sinal ${sig} enviado`);
      tick();
    } catch {
      setMsg("falha ao enviar sinal");
    }
  }

  async function tick() {
    const r = await fetch("/api/status").then((x) => x.json()).catch(() => null);
    if (r) setS(r);
    const hb = await fetch("/api/manual").then((x) => x.json()).catch(() => null);
    if (hb && !hb.error) setB(hb);
    const h = await fetch("/api/health").then((x) => x.json()).catch(() => null);
    if (h && typeof h.uptime === "number") setUptime(h.uptime);
  }

  useEffect(() => {
    tick();
    const i = setInterval(tick, 5000);
    return () => clearInterval(i);
  }, []);

  const alive = b && Date.now() - new Date(b.last_tick).getTime() < 45000;
  const pillStatus = !b ? "offline" : alive ? "online" : "degraded";
  const pillLabel = !b ? "aguardando bot" : alive ? "bot vivo" : "sem heartbeat";

  const tapeItems = [
    { symbol: b?.asset || "BTCUSD", price: `saldo ${b?.balance ?? s.balance}` },
    {
      symbol: "SESSÃO",
      price: `${s.profit >= 0 ? "+" : ""}${s.profit.toFixed(2)}`,
      chg: s.trades ? (s.winrate * 100 - 53.48) : 0,
    },
    { symbol: "WINRATE", price: `${(s.winrate * 100).toFixed(1)}%`, chg: s.trades ? s.winrate * 100 - 53.48 : 0 },
    { symbol: "ESTRATÉGIA", price: b?.strategy || "donchian_fade" },
    { symbol: "PAYOUT MÍN", price: "≥ 0.80" },
    { symbol: "TRADES", price: String(s.trades) },
  ];

  // Prepare chart data from last trades equity
  const chartData = s.last.map((t: any) => ({
    time: t.time || t.timestamp || "",
    profit: parseFloat(t.profit || 0),
    balance: parseFloat(t.balance || s.balance || 0),
  }));

  return (
    <div className="relative z-10 flex">
      <AppSidebar alive={!!alive} />
      <div className="flex-1 min-w-0">
        <main className="max-w-7xl mx-auto p-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <Brand />
          <p className="text-muted text-sm mt-2">
            PRACTICE · donchian_fade · payout ≥0.80{" "}
            {b ? `· ${b.asset} · saldo ${b.balance} · ${b.balance_type}` : ""}
          </p>
          {alive && b && (
            <p className="text-xs mt-1 text-muted">
              último tick {new Date(b.last_tick).toLocaleTimeString("pt-BR")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <SessionClock />
          <StatusPill status={pillStatus} label={pillLabel} />
          <CommandMenuHint />
        </div>
      </div>
      {msg && <p className="text-xs mt-2 text-muted">{msg}</p>}

      <div className="mt-4 -mx-6">
        <TickerTape items={tapeItems} />
      </div>

      {/* Alerts */}
      <div className="mt-4">
        <AlertsBanner trades={s.last} winrate={s.winrate} alive={!!alive} />
      </div>

      {/* Statistics Cards Row */}
      <div id="visao-geral" className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 scroll-mt-6">
        <StatisticsCard7 title="Total Trades" value={s.trades} subtitle="Sinais gerados" />
        <StatisticsCard7 title="Winrate" value={s.winrate} subtitle="Percentual de acertos" metric="winrate" />
        <StatisticsCard7 title="Lucro Sessão" value={s.profit} subtitle="Em R$" metric="profit" />
        <StatisticsCard7 title="Saldo Atual" value={s.balance} subtitle="Conta IQ Option" metric="balance" />
      </div>

      {/* Equity Curve Chart */}
      <div id="equity" className="mt-6 scroll-mt-6">
        <EquityCurveChart data={chartData} />
      </div>

      {/* Winrate trend + Payout distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <WinrateTrend trades={s.last} />
        <PayoutStats trades={s.last} />
      </div>

      {/* Profit bars + Payout scatter */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <ProfitBars trades={s.last} />
        <PayoutScatter trades={s.last} />
      </div>

      {/* Performance + Session */}
      <div id="desempenho" className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6 scroll-mt-6">
        <PerformanceGauge wins={s.wins} trades={s.trades} />
        <SessionSummary bot={b} uptime={uptime} />
      </div>

      {/* Drawdown + Equity stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <DrawdownCard trades={s.last} />
        <EquityStats trades={s.last} />
      </div>

      {/* Streak + Goal + Signal distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
        <StreakTracker trades={s.last} />
        <GoalRing session={s.profit} />
        <SignalDistribution trades={s.last} />
      </div>

      {/* Trade ticket + Strategy + Bot health */}
      <div id="operacao" className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6 scroll-mt-6">
        <TradeTicket />
        <StrategyConfig bot={b} />
        <BotHealthCard bot={b} uptime={uptime} />
      </div>

      {/* Ranking por ativo */}
      <div className="mt-6">
        <AssetRanking byAsset={s.byAsset} />
      </div>

      {/* Stake evolution + Session report */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <StakeEvolution trades={s.last} />
        <SessionReport
          trades={s.trades}
          wins={s.wins}
          winrate={s.winrate}
          profit={s.profit}
          balance={s.balance}
          asset={b?.asset}
          strategy={b?.strategy}
          uptime={uptime}
        />
      </div>

      {/* Atividade + Risco */}
      <div id="risco" className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6 scroll-mt-6">
        <TradesFeed trades={s.last.slice(0, 8)} />
        <RiskPanel last={s.last} balance={s.balance} />
      </div>

      {/* Full trade history with search/filter/export */}
      <div id="historico" className="mt-6 scroll-mt-6">
        <TradesHistoryFull trades={s.last} />
      </div>
        </main>
      </div>
      <CommandMenu onManual={manual} />
    </div>
  );
}