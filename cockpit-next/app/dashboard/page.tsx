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
import { useEffect, useState } from "react";

type S = {
  trades: number;
  wins: number;
  winrate: number;
  profit: number;
  balance: string;
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
    last: [],
  });

  const [b, setB] = useState<B>(null);
  const [uptime, setUptime] = useState(0);

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

  // Prepare chart data from last trades equity
  const chartData = s.last.map((t: any) => ({
    time: t.time || t.timestamp || "",
    profit: parseFloat(t.profit || 0),
    balance: parseFloat(t.balance || s.balance || 0),
  }));

  return (
    <main className="max-w-7xl mx-auto p-6">
      <div>
        <h1 className="text-2xl font-semibold">IQOperator — microfactx</h1>
        <p className="text-muted text-sm">
          PRACTICE · donchian_fade · payout ≥0.80{" "}
          {b ? `· ${b.asset} · saldo ${b.balance} · ${b.balance_type}` : ""}
        </p>
        <p className={`text-xs mt-1 ${alive ? "text-success" : "text-destructive"}`}>
          {alive
            ? `● bot vivo — último tick ${new Date(b!.last_tick).toLocaleTimeString()}`
            : "○ bot sem heartbeat (aguarde 5s)"}
        </p>
      </div>

      {/* Alerts */}
      <div className="mt-4">
        <AlertsBanner trades={s.last} winrate={s.winrate} alive={!!alive} />
      </div>

      {/* Statistics Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <StatisticsCard7 title="Total Trades" value={s.trades} subtitle="Sinais gerados" />
        <StatisticsCard7 title="Winrate" value={s.winrate} subtitle="Percentual de acertos" metric="winrate" />
        <StatisticsCard7 title="Lucro Sessão" value={s.profit} subtitle="Em R$" metric="profit" />
        <StatisticsCard7 title="Saldo Atual" value={s.balance} subtitle="Conta IQ Option" metric="balance" />
      </div>

      {/* Equity Curve Chart */}
      <div className="mt-6">
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
        <TradeTicket />
        <StrategyConfig bot={b} />
        <BotHealthCard bot={b} uptime={uptime} />
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <TradesFeed trades={s.last.slice(0, 8)} />
        <RiskPanel last={s.last} balance={s.balance} />
      </div>

      {/* Full trade history with search/filter/export */}
      <div className="mt-6">
        <TradesHistoryFull trades={s.last} />
      </div>
    </main>
  );
}