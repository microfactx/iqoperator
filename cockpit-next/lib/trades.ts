import fs from "fs";
export type Trade = { time:string; signal:string; info:string; payout:string; winrate:string; kelly:string; stake:string; profit:string; balance:string };
export function readTrades(): Trade[]{
  const p = process.env.TRADE_LOG || "data/trades_live.csv";
  try{
    const raw=fs.readFileSync(p,"utf-8").trim();
    if(!raw) return [];
    const lines=raw.split("\n"); const headers=lines[0].split(",");
    return lines.slice(1).filter(Boolean).map(l=>{
      const v=l.split(","); const o:Record<string,string>={};
      headers.forEach((h,i)=>o[h.trim()]=v[i]?.trim()||"");
      return o as Trade;
    });
  }catch{ return []; }
}
export function stats(){
  const rows=readTrades();
  const n=rows.length, wins=rows.filter(r=>parseFloat(r.profit||"0")>0).length;
  const wr=n?wins/n:0, profit=rows.reduce((s,r)=>s+parseFloat(r.profit||"0"),0);
  const bal=rows.at(-1)?.balance ?? "n/a";
  return { trades:n, wins, winrate:wr, profit:Math.round(profit*100)/100, balance:bal, last: rows.slice(-10).reverse() };
}
