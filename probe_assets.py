"""Probe de ativos IQOption — testa abertura/payout/candles sem comprar (default).

Uso:
    python -u probe_assets.py                     # dry-run: só leitura
    python -u probe_assets.py --live              # + 1 buy mínimo ($1) por ativo aprovado
    python -u probe_assets.py --assets EURUSD-OTC,BTCUSD --live --stake 1

Critério de aprovação: binary OU turbo aberto + payout >= IQ_PAYOUT_MIN + candles M15 OK.
O teste live compra 1x CALL stake mínimo e NÃO aguarda o resultado (só valida aceite).
Sempre em PRACTICE por segurança.

Obs: a iqoptionapi tem busy-loops internos (`while x is None: pass`) que podem
pendurar se o servidor não responder — por isso cada chamada bloqueante roda
numa thread daemon com timeout (fail-fast em vez de travar para sempre).
Use sempre `python -u` (stdout sem buffer) para acompanhar o progresso.
"""
import argparse
import os
import queue
import sys
import threading
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

DEFAULT_ASSETS = [
    "EURUSD", "EURUSD-OTC",
    "GBPUSD", "GBPUSD-OTC",
    "USDJPY", "USDJPY-OTC",
    "AUDUSD", "AUDUSD-OTC",
    "EURGBP-OTC", "USDCAD-OTC",
    "BTCUSD", "BTCUSD-OTC",
    "ETHUSD", "ETHUSD-OTC",
]


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def run_with_timeout(fn, timeout: float, label: str):
    """Roda fn() numa thread daemon; se estourar timeout, desiste e retorna (False, None)."""
    q: queue.Queue = queue.Queue()

    def _w():
        try:
            q.put((True, fn()))
        except Exception as e:  # noqa: BLE001
            q.put((False, f"{type(e).__name__}: {e}"))

    t = threading.Thread(target=_w, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return False, f"TIMEOUT após {timeout:.0f}s em {label}"
    try:
        return q.get_nowait()
    except queue.Empty:
        return False, f"sem resposta em {label}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default=",".join(DEFAULT_ASSETS))
    ap.add_argument("--live", action="store_true", help="faz 1 buy $1 por ativo aprovado")
    ap.add_argument("--stake", type=float, default=1.0)
    ap.add_argument("--payout-min", type=float, default=float(os.getenv("IQ_PAYOUT_MIN", "0.80")))
    ap.add_argument("--connect-timeout", type=float, default=90)
    ap.add_argument("--stage-timeout", type=float, default=120)
    ap.add_argument("--candle-timeout", type=float, default=45)
    args = ap.parse_args()

    from iqoptionapi.stable_api import IQ_Option

    email, pwd = os.getenv("IQ_EMAIL", ""), os.getenv("IQ_PASSWORD", "")
    if not email or not pwd:
        print("Faltam IQ_EMAIL/IQ_PASSWORD no .env", file=sys.stderr)
        return 2

    api = IQ_Option(email, pwd)
    log("conectando...")
    ok, res = run_with_timeout(api.connect, args.connect_timeout, "connect")
    if not ok or not res or not res[0]:
        log(f"connect falhou: {res}")
        return 1
    log("conectado. Mudando para PRACTICE...")
    ok, res = run_with_timeout(lambda: (api.change_balance("PRACTICE"), api.get_balance()),
                               60, "change_balance")
    log(f"PRACTICE saldo={res if ok else res}")

    log("update_ACTIVES_OPCODE...")
    ok, res = run_with_timeout(api.update_ACTIVES_OPCODE, args.stage_timeout, "update_ACTIVES_OPCODE")
    log(f"actives: {'OK' if ok else res}")

    log("get_all_open_time (pode levar ~1-2 min)...")
    ok_ot, open_time = run_with_timeout(api.get_all_open_time, 180, "get_all_open_time")
    if not ok_ot:
        log(f"get_all_open_time falhou: {open_time}")
        open_time = {}
    else:
        log("open_time OK")

    log("get_all_profit...")
    ok_pf, profits = run_with_timeout(api.get_all_profit, args.stage_timeout, "get_all_profit")
    if not ok_pf:
        log(f"get_all_profit falhou: {profits}")
        profits = {}
    else:
        log("profits OK")

    assets = [a.strip() for a in args.assets.split(",") if a.strip()]
    approved: list[tuple[str, int]] = []  # (asset, expiration para live)
    print(f"\n{'ativo':<14}{'bin_open':<10}{'bin_pay':<9}{'turbo_open':<12}{'turbo_pay':<11}candles", flush=True)
    for asset in assets:
        try:
            bin_open = open_time.get("binary", {}).get(asset, {}).get("open", "?")
        except Exception:
            bin_open = "?"
        try:
            tb_open = open_time.get("turbo", {}).get(asset, {}).get("open", "?")
        except Exception:
            tb_open = "?"
        try:
            v = profits.get(asset, {}).get("binary", None)
            bin_pay = round(float(v), 2) if v is not None else None
        except Exception:
            bin_pay = None
        try:
            v = profits.get(asset, {}).get("turbo", None)
            tb_pay = round(float(v), 2) if v is not None else None
        except Exception:
            tb_pay = None

        ok_c, candles = run_with_timeout(
            lambda a=asset: api.get_candles(a, 900, 5, time.time()),
            args.candle_timeout, f"get_candles {asset}")
        if ok_c and candles:
            candles_ok = f"OK({len(candles)})"
        elif ok_c:
            candles_ok = "VAZIO"
        else:
            candles_ok = f"ERRO {str(candles)[:40]}"

        print(f"{asset:<14}{str(bin_open):<10}{str(bin_pay):<9}"
              f"{str(tb_open):<12}{str(tb_pay):<11}{candles_ok}", flush=True)

        # open_time pode falhar (get_all_init instável); payout presente ~= ofertado.
        # "?" + payout >= mínimo conta como presuntivamente aberto.
        def _open(v):
            return v is True or v == "?"

        exp = None
        if _open(bin_open) and bin_pay is not None and bin_pay >= args.payout_min \
                and candles_ok.startswith("OK"):
            exp = 15
        elif _open(tb_open) and tb_pay is not None and tb_pay >= args.payout_min \
                and candles_ok.startswith("OK"):
            exp = 1
        if exp:
            approved.append((asset, exp))

    print(f"\nAprovados ({len(approved)}): {[a for a, _ in approved] or 'nenhum'}", flush=True)
    if not args.live:
        print("dry-run: nenhuma compra feita. Rode com --live para testar 1 buy $1 por aprovado.",
              flush=True)
        return 0

    for asset, exp in approved:
        ok, order = run_with_timeout(
            lambda a=asset, e=exp: api.buy(args.stake, a, "call", e),
            30, f"buy {asset}")
        if ok and isinstance(order, tuple):
            accepted, oid = order
            print(f"[LIVE] CALL {asset} M{exp} stake={args.stake} -> "
                  f"{'ACEITO' if accepted else 'REJEITADO'}: {oid}", flush=True)
        else:
            print(f"[LIVE] CALL {asset} M{exp} -> ERRO/TIMEOUT: {order}", flush=True)
        time.sleep(2)
    print("live-test concluído. Posições PRACTICE expiram sozinhas; confira saldo/extrato.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
