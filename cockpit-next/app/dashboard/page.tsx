import { stats } from "@/lib/trades";
export default function Dashboard(){
  const s=stats();
  return (<main className="max-w-6xl mx-auto p-6">
    <h1 className="text-2xl font-semibold">IQOperator — microfactx</h1>
    <p className="text-muted text-sm">PRACTICE · donchian_fade · payout ≥0.80</p>
    <div className="grid grid-cols-4 gap-4 mt-6">
      <div className="bg-surface border border-border rounded-lg p-4"><div className="text-muted text-xs">Trades</div><div className="text-xl font-bold">{s.trades}</div></div>
      <div className="bg-surface border border-border rounded-lg p-4"><div className="text-muted text-xs">Winrate</div><div className="text-xl font-bold">{(s.winrate*100).toFixed(1)}%</div></div>
      <div className="bg-surface border border-border rounded-lg p-4"><div className="text-muted text-xs">Lucro</div><div className={`text-xl font-bold ${s.profit>=0?'text-success':'text-destructive'}`}>{s.profit}</div></div>
      <div className="bg-surface border border-border rounded-lg p-4"><div className="text-muted text-xs">Saldo</div><div className="text-xl font-bold">{s.balance}</div></div>
    </div>
    <p className="mt-8 text-muted text-sm">Full cockpit com auth Google + Postgres em construção nesta branch.</p>
  </main>);
}
