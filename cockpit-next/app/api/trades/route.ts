import fs from "fs";
export const dynamic="force-dynamic";
export async function GET(){
  const p=process.env.TRADE_LOG||"data/trades_live.csv";
  try{ const b=fs.readFileSync(p); return new Response(b,{headers:{"Content-Type":"text/csv"}});}catch{ return new Response("not found",{status:404});}
}
