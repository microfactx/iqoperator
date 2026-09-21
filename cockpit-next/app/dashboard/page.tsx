"use client";
import { DataGridTable } from "@/components/data-grid-table";
import { StatisticsCard7 } from "@/components/statistics-card-7";
import { EquityCurveChart } from "@/components/line-charts-9";
import { cn } from "@/lib/utils";
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

  const [msg, setMsg] = useState("");

  async function tick() {
    const r = await fetch("/api/status").then((x) => x.json()).catch(() => null);
    if (r) setS(r);
    const hb = await fetch("/api/manual").then((x) => x.json()).catch(() => null);
    if (hb && !hb.error) setB(hb);
  }

  useEffect(() => {
    tick();
    const i = setInterval(tick, 5000);
    return () => clearInterval(i);
  }, []);

  async function manual(sig: "call" | "put") {
    if (!confirm(`Enviar ${sig.toUpperCase()} manual?`)) return;
    const r = await fetch("/api/manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signal: sig }),
    });
    setMsg(r.ok ? `Enviado ${sig.toUpperCase()} — o bot executa em até 5s` : "Erro");
    setTimeout(() => setMsg(""), 4000);
  }

  const alive =
    b && Date.now() - new Date(b.last_tick).getTime() < 45000;

  // Prepare chart data from last trades equity
  const chartData = s.last.map((t: any) => ({
    time: t.time || t.timestamp || "",
    profit: parseFloat(t.profit || 0),
    balance: parseFloat(t.balance || s.balance || 0),
  }));

  return (
    <main className="max-w-7xl mx-auto p-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-semibold">
            IQOperator — microfactx
          </h1>
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
        <div className="flex gap-2">
          <button
            onClick={() => manual("call")}
            className="bg-success text-black font-bold px-6 py-3 rounded-lg hover:opacity-90"
          >
            CALL ▲
          </button>
          <button
            onClick={() => manual("put")}
            className="bg-destructive text-white font-bold px-6 py-3 rounded-lg hover:opacity-90"
          >
            PUT ▼
          </button>
        </div>
      </div>

      {msg && (
        <div className="mt-3 bg-surface border border-border rounded p-2 text-sm">
          {msg}
        </div>
      )}

      {/* Statistics Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <StatisticsCard7
          title="Total Trades"
          value={s.trades}
          subtitle="Sinais gerados"
        />
        <StatisticsCard7
          title="Winrate"
          value={s.winrate}
          subtitle="Percentual de acertos"
          metric="winrate"
        />
        <StatisticsCard7
          title="Lucro Sessão"
          value={s.profit}
          subtitle="Em R$"
          metric="profit"
        />
        <StatisticsCard7
          title="Saldo Atual"
          value={s.balance}
          subtitle="Conta IQ Option"
          metric="balance"
        />
      </div>

      {/* Equity Curve Chart */}
      <div className="mt-6">
        <EquityCurveChart data={chartData} />
      </div>

      {/* Trade History Table */}
      <div className="mt-6 bg-surface border border-border rounded-lg p-4">
        <h2 className="text-sm font-medium mb-4">Histórico das Últimas Trades</h2>
        <DataGridTable
          columns={[
            { accessorKey: "time", header: "Hora" },
            { accessorKey: "signal", header: "Sinal" },
            { accessorKey: "profit", header: "Lucro" },
            { accessorKey: "balance", header: "Saldo" },
          ]}
          data={s.last}
          width="full"
        />
      </div>
    </main>
  );
}