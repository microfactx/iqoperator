"""Entrypoint p/ Hugging Face Space: bot + página de status na porta 7860 (stdlib)."""
import csv
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from bot import Bot

STARTED = time.time()
BOT: Bot | None = None


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: str, code: int = 200):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        up = int(time.time() - STARTED)
        profit = f"{BOT.profit:+.2f}" if BOT else "n/a"
        ntrades = wins = "n/a"
        last = []
        try:
            with open("data/trades_live.csv", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            ntrades = len(rows)
            wins = sum(1 for r in rows if float(r["profit"]) > 0)
            last = rows[-10:]
        except (FileNotFoundError, ValueError):
            pass
        items = "".join(
            f"<li>{r['time']} {r['signal']} stake={r['stake']} lucro={r['profit']}</li>"
            for r in last)
        self._send(
            f"<h1>IQOperator (demo)</h1>"
            f"<p>uptime: {up//3600}h {(up%3600)//60}m | sessao: {profit} | "
            f"trades: {ntrades} wins: {wins}</p>"
            f"<p>atualizado: {datetime.now(timezone.utc).isoformat(timespec='seconds')}</p>"
            f"<h2>Ultimos trades</h2><ul>{items}</ul>")

    def log_message(self, *a):
        pass


def serve():
    port = int(os.getenv("PORT", "7860"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=serve, daemon=True).start()
    BOT = Bot()
    BOT.run()
