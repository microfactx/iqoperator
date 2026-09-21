export async function GET(){ return Response.json({ ok:true, uptime: process.uptime() }); }
