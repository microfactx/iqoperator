import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";
export const dynamic="force-dynamic";
function resolve(p:string, forWrite=false){
  if(path.isAbsolute(p)) return p;
  const cand=[path.join(process.cwd(), p), path.join(process.cwd(),"..",p), path.join("/app",p)];
  if(forWrite) return cand[1].endsWith(".json") ? cand[1] : cand[0];
  for(const c of cand) if(fs.existsSync(c)) return c;
  return cand[1];
}

export async function POST(req: Request){
  const { signal } = await req.json().catch(()=>({}));
  if(signal!=="call" && signal!=="put") return NextResponse.json({error:"signal must be call|put"}, {status:400});
  const p = resolve(process.env.MANUAL_SIGNAL || "data/manual_signal.json", true);
  fs.mkdirSync(path.dirname(p), {recursive:true});
  fs.writeFileSync(p, JSON.stringify({signal, ts: Date.now()/1000}));
  return NextResponse.json({ok:true, signal});
}
export async function GET(){
  try{
    const p=resolve(process.env.BOT_STATUS||"data/bot_status.json", false);
    const b = JSON.parse(fs.readFileSync(p,"utf-8"));
    return NextResponse.json(b);
  }catch{ return NextResponse.json({error:"no status yet"}, {status:404}); }
}
