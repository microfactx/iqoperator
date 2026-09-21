import fs from "fs";
import { NextResponse } from "next/server";
export const dynamic="force-dynamic";

export async function POST(req: Request){
  const { signal } = await req.json().catch(()=>({}));
  if(signal!=="call" && signal!=="put") return NextResponse.json({error:"signal must be call|put"}, {status:400});
  const p = process.env.MANUAL_SIGNAL || "data/manual_signal.json";
  fs.mkdirSync("data", {recursive:true});
  fs.writeFileSync(p, JSON.stringify({signal, ts: Date.now()/1000}));
  return NextResponse.json({ok:true, signal});
}
export async function GET(){
  try{
    const b = JSON.parse(fs.readFileSync(process.env.BOT_STATUS||"data/bot_status.json","utf-8"));
    return NextResponse.json(b);
  }catch{ return NextResponse.json({error:"no status yet"}, {status:404}); }
}
