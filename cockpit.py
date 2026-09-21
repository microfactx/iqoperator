"""Cockpit web para Railway — status do bot sem disco.

Rota /          : HTML com auto-refresh
Rota /api/status: JSON (uptime, trades, winrate, profit, saldo, ultimos trades)
Rota /api/trades: CSV raw
"""
import csv
import json
import os
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

STARTED = time.time()
BOT_REF: object = None


def _read_trades():
    path = os.getenv("TRADE_LOG", "data/trades_live.csv")
    try:
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return rows
    except Exception:
        return []


def _stats():
    rows = _read_trades()
    n = len(rows)
    wins = sum(1 for r in rows if float(r.get("profit", 0) or 0) > 0)
    wr = wins / n if n else 0
    profit = sum(float(r.get("profit", 0) or 0) for r in rows)
    bal = rows[-1].get("balance", "n/a") if rows else "n/a"
    up = int(time.time() - STARTED)
    return {
        "uptime": f"{up//3600}h {(up%3600)//60}m",
        "trades": n, "wins": wins, "winrate": round(wr, 4),
        "profit": round(profit, 2), "balance": bal,
        "last": rows[-10:] if rows else [],
    }


HTML = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>IQOperator Cockpit</title><style>
body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;background:#0b0e14;color:#e6e6e6}
h1{margin:0 0 .3rem} .sub{color:#8a8f98;margin-bottom:1.2rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.8rem;margin:1rem 0}
.card{background:#151a23;border:1px solid #232a36;border-radius:10px;padding:1rem}
.card b{font-size:1.4rem;display:block} .ok{color:#3dd68c} .bad{color:#ff5470}
table{width:100%;border-collapse:collapse;margin-top:1rem;font-size:.9rem}
th,td{border-bottom:1px solid #232a36;padding:.4rem .5rem;text-align:left}
th{color:#8a8f98} a{color:#5ea1ff}
.mono{font-family:ui-monospace,monospace;font-size:.85rem}
</style></head><body>
<h1>IQOperator — Cockpit</h1><div class=sub id=sub>carregando…</div>
<div class=cards id=cards></div>
<h2>Ultimos trades</h2><table><thead><tr><th>hora</th><th>sinal</th><th>info</th><th>stake</th><th>lucro</th><th>saldo</th></tr></thead><tbody id=tbody></tbody></table>
<p style="margin-top:1.5rem"><a href="/api/status">/api/status</a> · <a href="/api/trades">/api/trades (CSV)</a> · <a href="https://huggingface.co/datasets/jonatanciamarro/iqoperator-trades" target=_blank>HF bucket</a></p>
<script>
async function tick(){
  const r=await fetch('/api/status'); const j=await r.json();
  document.getElementById('sub').textContent=`uptime ${j.uptime} · payout min 0.80 · estrategia donchian_fade`;
  document.getElementById('cards').innerHTML=`
    <div class=card><span>Trades</span><b>${j.trades}</b></div>
    <div class=card><span>Wins</span><b class=${j.winrate>=0.5348?'ok':'bad'}>${j.wins} (${(j.winrate*100).toFixed(1)}%)</b></div>
    <div class=card><span>Lucro sessao</span><b class=${j.profit>=0?'ok':'bad'}>${j.profit>=0?'+':''}${j.profit}</b></div>
    <div class=card><span>Saldo</span><b>${j.balance}</b></div>`;
  document.getElementById('tbody').innerHTML=j.last.map(t=>`<tr><td class=mono>${t.time||''}</td><td>${t.signal||''}</td><td>${t.info||''}</td><td>${t.stake||''}</td><td class=${parseFloat(t.profit||0)>=0?'ok':'bad'}>${t.profit||''}</td><td>${t.balance||''}</td></tr>`).join('')||'<tr><td colspan=6>sem trades ainda</td></tr>';
}
tick(); setInterval(tick, 15000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _html(self, s):
        b = s.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/status":
            return self._json(_stats())
        if self.path == "/api/trades":
            p = os.getenv("TRADE_LOG", "data/trades_live.csv")
            try:
                with open(p, "rb") as f:
                    b = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return
            except FileNotFoundError:
                self.send_response(404); self.end_headers(); return
        self._html(HTML)

    def log_message(self, *a): pass


def start_in_thread():
    port = int(os.getenv("PORT", "8080"))
    def serve():
        HTTPServer(("0.0.0.0", port), Handler).serve_forever()
    threading.Thread(target=serve, daemon=True).start()
