"""Robô IQOption DEMO - Binárias multi-ativo OTC | donchian_fade M15 + Kelly 2%.

- Opera todos os cfg.ASSETS em ciclo sequencial (1 scan ~= todos os ativos).
- Resultado de trade NÃO bloqueia o loop: posições ficam em self.pending e são
  conciliadas a cada ciclo (_reconcile_pending) via get_betinfo pontual.
- Trava global: no máximo cfg.MAX_CONCURRENT posições pendentes simultâneas
  (manual via cockpit bypassa a trava, com log explícito).
- Log de trades com coluna asset; arquivo legado sem a coluna é preservado
  como *_legacy.csv e um novo é iniciado.
"""
import csv
import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
import pandas as pd
from iqoptionapi.stable_api import IQ_Option

import config as cfg
from strategies import get_signal, rsi_series
from kelly import kelly_fraction_stake, empirical_winrate
from hf_sync import sync_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(cfg.LOG_FILE, encoding="utf-8"),
              logging.StreamHandler()],
)
log = logging.getLogger("iqrobot")

TRADE_HEADER = ["time", "asset", "signal", "info", "payout", "winrate",
                "kelly", "stake", "profit", "balance"]


class Bot:
    def __init__(self):
        self.api = IQ_Option(cfg.EMAIL, cfg.PASSWORD)
        self.assets = list(cfg.ASSETS)
        self.profit = 0.0
        self.asset_profit = {a: 0.0 for a in self.assets}
        self.history: dict[str, deque] = {a: deque(maxlen=cfg.KELLY_LOOKBACK) for a in self.assets}
        self.buys_attempted = 0
        self.buys_rejected = 0
        self.last_signal: dict[str, str | None] = {}
        self.last_payout: dict[str, float] = {}
        self.last_candle_key: dict[str, str] = {}
        self.last_check: dict[str, str] = {}
        self.pending: list[dict] = []
        self.martingale_step = 0
        self.current_amount = cfg.AMOUNT
        self._detail_cache: tuple[float, object] = (0.0, None)
        self._last_balance: float | None = None
        self._last_progress = time.time()
        self._trade_log_init()
        self._load_pending()

    # ---------- chamadas com timeout ----------
    @staticmethod
    def _call_timeout(fn, timeout: float, label: str):
        """Roda fn() com prazo; estourou -> (False, 'TIMEOUT...'). Nunca trava o loop."""
        import queue
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
        except Exception:
            return False, f"sem resposta em {label}"

    def _safe_balance(self, timeout: float = 20) -> float:
        ok, res = self._call_timeout(lambda: float(self.api.get_balance() or 0),
                                     timeout, "get_balance")
        if ok:
            self._last_balance = res
            return res
        log.warning(f"get_balance falhou ({res}); usando último conhecido.")
        return self._last_balance or 0.0

    def _touch_progress(self):
        self._last_progress = time.time()

    def _start_watchdog(self):
        def _w():
            while True:
                time.sleep(30)
                idle = time.time() - self._last_progress
                if idle > cfg.WATCHDOG_TIMEOUT:
                    log.error(f"WATCHDOG: sem progresso há {idle:.0f}s — reiniciando processo.")
                    os._exit(1)
        threading.Thread(target=_w, daemon=True).start()

    # ---------- pendências em disco ----------
    def _save_pending(self):
        try:
            os.makedirs(os.path.dirname(cfg.PENDING_FILE) or ".", exist_ok=True)
            with open(cfg.PENDING_FILE, "w", encoding="utf-8") as f:
                json.dump(self.pending, f)
        except Exception as e:
            log.warning(f"save_pending: {e}")

    def _load_pending(self):
        try:
            if not os.path.exists(cfg.PENDING_FILE):
                return
            with open(cfg.PENDING_FILE, encoding="utf-8") as f:
                orders = json.load(f)
            now = time.time()
            kept = [o for o in orders if isinstance(o, dict) and o.get("deadline", 0) > now]
            dropped = len(orders) - len(kept)
            if dropped:
                log.warning(f"Descartando {dropped} pendência(s) expirada(s) do restart.")
            self.pending = kept
            if kept:
                log.info(f"Recuperadas {len(kept)} pendência(s) do disco.")
        except Exception as e:
            log.warning(f"load_pending: {e}")

    # ---------- log de trades ----------
    def _trade_log_init(self):
        if not os.path.exists(cfg.TRADE_LOG):
            os.makedirs(os.path.dirname(cfg.TRADE_LOG) or ".", exist_ok=True)
            with open(cfg.TRADE_LOG, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(TRADE_HEADER)
            return
        try:
            with open(cfg.TRADE_LOG, encoding="utf-8") as f:
                header = f.readline().strip().split(",")
            if header != TRADE_HEADER:
                legacy = cfg.TRADE_LOG.replace(".csv", "_legacy.csv")
                os.rename(cfg.TRADE_LOG, legacy)
                log.info(f"Trade log legado preservado em {legacy}; iniciando novo com coluna asset.")
                with open(cfg.TRADE_LOG, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(TRADE_HEADER)
        except Exception as e:
            log.warning(f"trade_log_init: {e}")

    def _trade_log(self, row: list):
        with open(cfg.TRADE_LOG, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        # sem disco no Railway: espelha no dataset HF (se HF_TOKEN + HF_DATASET_REPO setados)
        sync_file(cfg.TRADE_LOG)

    # ---------- conexão ----------
    def connect(self) -> bool:
        for attempt in range(1, 6):
            try:
                ok, reason = self.api.connect()
                if ok:
                    self.api.change_balance(cfg.BALANCE_TYPE)
                    log.info(f"Conectado | Conta: {cfg.BALANCE_TYPE} | Saldo: {self.api.get_balance()}")
                    return True
                log.warning(f"Connect falhou (tent. {attempt}): {reason}")
            except Exception as e:
                log.warning(f"Connect exceção (tent. {attempt}): {e}")
            time.sleep(10 * attempt)
        return False

    def ensure_connected(self) -> bool:
        try:
            if self.api.check_connect():
                return True
        except Exception:
            pass
        log.warning("Conexão perdida, reconectando...")
        return self.connect()

    # ---------- dados ----------
    def candles_df(self, asset: str, timeframe: int, count: int,
                   timeout: float = 30) -> pd.DataFrame | None:
        # A lib entra em `while True + reconnect` se a conexão cair no meio do
        # get_candles — sem timeout, 1 ativo congela o scan inteiro (e o heartbeat).
        # Roda com prazo: estourou, pula o ativo neste ciclo.
        ok, res = self._call_timeout(
            lambda: self.api.get_candles(asset, timeframe, count, time.time()),
            timeout, f"get_candles {asset}")
        if not ok:
            log.warning(f"get_candles {asset}: {res} — pulando ciclo.")
            return None
        candles = res
        if not candles:
            return None
        df = pd.DataFrame(candles)
        df = df.rename(columns={"max": "high", "min": "low"})
        for c in ("high", "low", "close", "open"):
            if c not in df.columns:
                df[c] = df.get("close", 0)
        return df

    def _fetch_detail(self):
        """get_binary_option_detail com cache de 120s (a chamada é lenta/instável)."""
        ts, cached = self._detail_cache
        if cached is not None and time.time() - ts < 120:
            return cached
        ok, detail = self._call_timeout(self.api.get_binary_option_detail, 90, "get_all_init")
        if not ok:
            log.warning(f"detail fallback: {detail}")
            return cached  # usa último conhecido (pode ser None)
        self._detail_cache = (time.time(), detail)
        return detail

    def get_payout(self, asset: str, detail=None) -> float:
        try:
            if detail is None:
                detail = self.api.get_binary_option_detail()
            v = detail.get(asset) if isinstance(detail, dict) else None
            if isinstance(v, dict):
                # estrutura real: {"binary": {"option": {"profit": {"commission": X}}}, ...}
                for k in ("binary", "turbo"):
                    sub = v.get(k)
                    if isinstance(sub, dict):
                        try:
                            commission = float(sub["option"]["profit"]["commission"])
                            return round((100.0 - commission) / 100.0, 4)
                        except (KeyError, TypeError, ValueError):
                            pass
                for k in ("profit", "payout", "turbo", "binary"):
                    if k in v:
                        num = v[k]
                        if isinstance(num, dict):
                            num = next(iter(num.values()), None)
                        if isinstance(num, (int, float)):
                            return float(num) / 100 if num > 1 else float(num)
            elif isinstance(v, (int, float)):
                return float(v) / 100 if v > 1 else float(v)
        except Exception as e:
            log.warning(f"payout fallback {asset}: {e}")
        return cfg.KELLY_PAYOUT_DEFAULT

    def calc_stake(self, asset: str, payout: float) -> tuple[float, float, float]:
        balance = self._safe_balance()
        p = empirical_winrate(list(self.history[asset]), cfg.KELLY_PRIOR,
                              prior_weight=cfg.KELLY_PRIOR_WEIGHT)
        if cfg.USE_KELLY:
            stake, kfull = kelly_fraction_stake(
                balance, payout, p, fraction=cfg.KELLY_FRACTION,
                max_risk=cfg.KELLY_MAX_RISK, min_amount=cfg.KELLY_MIN)
            return stake, p, kfull
        return round(self.current_amount, 2), p, 0.0

    # ---------- execução não-bloqueante ----------
    def _fire_buy(self, asset: str, action: str, stake: float):
        """Dispara o buy e retorna order dict (sem aguardar resultado)."""
        self.buys_attempted += 1
        balance_before = self._safe_balance()
        ok, res = self._call_timeout(
            lambda: self.api.buy(stake, asset, action, cfg.EXPIRATION),
            30, f"buy {asset}")
        if not ok:
            self.buys_rejected += 1
            log.error(f"Buy TIMEOUT ({self.buys_rejected}/{self.buys_attempted}): {res} (ativo={asset})")
            return None
        ok2, order_id = res
        if not ok2:
            self.buys_rejected += 1
            log.error(f"Buy rejeitado ({self.buys_rejected}/{self.buys_attempted}): {order_id} (ativo={asset})")
            return None
        log.info(f"TRADE {action.upper()} {asset} M{cfg.EXPIRATION} stake={stake} id={order_id}")
        return {"order_id": order_id, "asset": asset, "action": action,
                "stake": stake, "balance_before": balance_before,
                "deadline": time.time() + cfg.EXPIRATION * 60 + 180,
                "signal": None, "info": None, "payout": None, "p": None, "kfull": None}

    def _poll_pending(self, order: dict) -> float | None:
        """Uma consulta pontual de resultado; None = ainda pendente/desconhecido."""
        ok, res = self._call_timeout(
            lambda: self.api.get_betinfo(order["order_id"]), 30,
            f"get_betinfo {order['order_id']}")
        if not ok:
            log.warning(f"get_betinfo id={order['order_id']}: {res}")
            return None
        try:
            ok2, data = res
        except (TypeError, ValueError):
            return None
        if ok2 and data:
            try:
                node = data["result"]["data"][str(order["order_id"])]
            except KeyError:
                return None
            if node.get("win") not in ("", None):
                try:
                    return float(node["profit"]) - float(node["deposit"])
                except (KeyError, TypeError, ValueError):
                    return None
        return None

    def _settle(self, order: dict, profit: float, estimated: bool = False):
        tag = "RESULT_TIMEOUT(est)" if estimated else ("WIN" if profit > 0 else "LOSS")
        self.update_result(order["asset"], order.get("signal") or order["action"],
                           order.get("info") or "AUTO", order.get("payout") or 0,
                           order.get("p") or 0, order.get("kfull") or 0,
                           order["stake"], round(profit, 2))
        log.info(f"{tag} {order['asset']} {profit:+.2f} id={order['order_id']}")

    def _reconcile_pending(self):
        for order in list(self.pending):
            profit = self._poll_pending(order)
            if profit is not None:
                self.pending.remove(order)
                self._save_pending()
                self._settle(order, profit)
                continue
            if time.time() > order["deadline"]:
                self.pending.remove(order)
                self._save_pending()
                balance_now = self._safe_balance()
                est = round(balance_now - order["balance_before"], 2)
                log.warning(f"RESULT_TIMEOUT id={order['order_id']} — sem betinfo; profit estimado via saldo: {est:+.2f}")
                self._settle(order, est, estimated=True)

    # ---------- resultado ----------
    def update_result(self, asset: str, signal: str, info: object, payout: float,
                      p: float, kfull: float, stake: float, profit: float):
        self.profit += profit
        self.asset_profit[asset] = self.asset_profit.get(asset, 0.0) + profit
        won = profit > 0
        self.history[asset].append(won)
        balance = self._safe_balance()
        tag = "WIN" if won else "LOSS"
        wr = empirical_winrate(list(self.history[asset]), cfg.KELLY_PRIOR,
                               prior_weight=cfg.KELLY_PRIOR_WEIGHT)
        log.info(f"{tag} {asset} {profit:+.2f} | Sessão {self.profit:+.2f} | saldo {balance} | wr {wr:.2f}")
        self._trade_log([datetime.now().isoformat(timespec="seconds"), asset, signal,
                         info, round(payout, 4), round(p, 4),
                         kfull, stake, round(profit, 2), balance])
        self._write_status()

    def _candle_key(self, df) -> str:
        """Chave robusta do último candle (várias versões da API usam 'from'/'at'/etc)."""
        last = df.iloc[-1]
        for col in ("from", "at", "open_time", "time", "date", "timestamp"):
            if col in df.columns:
                try:
                    v = int(float(last[col]))
                    if v > 0:
                        return f"{col}:{v}"
                except (TypeError, ValueError):
                    continue
        # fallback: usa o close (avalia todo loop, sem dedup por tempo)
        try:
            return f"noclock:{float(last['close'])}"
        except (TypeError, ValueError, KeyError):
            return f"row:{len(df)}"

    def _write_status(self):
        try:
            self._touch_progress()
            os.makedirs(os.path.dirname(cfg.BOT_STATUS) or ".", exist_ok=True)
            per_asset = []
            for a in self.assets:
                wr = empirical_winrate(list(self.history[a]), cfg.KELLY_PRIOR,
                                       prior_weight=cfg.KELLY_PRIOR_WEIGHT)
                per_asset.append({
                    "asset": a,
                    "profit_session": round(self.asset_profit.get(a, 0.0), 2),
                    "trades": len(self.history[a]),
                    "winrate": round(wr, 4),
                    "last_signal": self.last_signal.get(a),
                    "last_payout": self.last_payout.get(a),
                    "last_check": self.last_check.get(a),
                })
            with open(cfg.BOT_STATUS, "w", encoding="utf-8") as f:
                json.dump({
                    "last_tick": datetime.now(timezone.utc).isoformat(),
                    "asset": f"multi:{len(self.assets)}",
                    "assets": per_asset,
                    "balance": self._safe_balance() if hasattr(self, 'api') else None,
                    "balance_type": cfg.BALANCE_TYPE,
                    "strategy": cfg.STRATEGY,
                    "profit_session": round(self.profit, 2),
                    "trades": sum(len(h) for h in self.history.values()),
                    "buys_attempted": self.buys_attempted,
                    "buys_rejected": self.buys_rejected,
                    "pending": len(self.pending),
                    "max_concurrent": cfg.MAX_CONCURRENT,
                }, f)
        except Exception:
            pass

    def _check_manual(self) -> dict | None:
        try:
            if not os.path.exists(cfg.MANUAL_SIGNAL):
                return None
            with open(cfg.MANUAL_SIGNAL, encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("ts", 0)
            if time.time() - ts > 60:
                os.remove(cfg.MANUAL_SIGNAL)
                return None
            sig = data.get("signal")
            if sig not in ("call", "put"):
                os.remove(cfg.MANUAL_SIGNAL)
                return None
            os.remove(cfg.MANUAL_SIGNAL)
            asset = str(data.get("asset") or self.assets[0]).upper()
            if asset not in self.assets:
                log.warning(f"MANUAL ignorado: ativo {asset} fora da lista {self.assets}")
                return None
            stake = data.get("stake")
            try:
                stake = float(stake) if stake is not None else None
            except (TypeError, ValueError):
                stake = None
            log.info(f"MANUAL {sig.upper()} {asset} solicitado via cockpit")
            return {"signal": sig, "asset": asset, "stake": stake}
        except Exception as e:
            log.warning(f"manual check falhou: {e}")
            return None

    def _manual_stake(self, asset: str, payout: float, want: float | None) -> tuple[float, float, float]:
        if want is not None and want > 0:
            balance = self._safe_balance()
            cap = max(balance * 0.05, cfg.KELLY_MIN)
            if want <= cap:
                p = empirical_winrate(list(self.history[asset]), cfg.KELLY_PRIOR,
                                      prior_weight=cfg.KELLY_PRIOR_WEIGHT)
                return round(want, 2), p, 0.0
            log.warning(f"MANUAL stake {want} acima do teto {cap:.2f}; usando Kelly.")
        return self.calc_stake(asset, payout)

    def stop(self) -> bool:
        if self.profit >= cfg.STOP_WIN:
            log.info(f"STOP WIN {self.profit:.2f}")
            return True
        if self.profit <= -cfg.STOP_LOSS:
            log.info(f"STOP LOSS {self.profit:.2f}")
            return True
        return False

    def run(self):
        if not cfg.EMAIL or not cfg.PASSWORD:
            log.error("Configure IQ_EMAIL e IQ_PASSWORD no .env")
            return
        if cfg.BALANCE_TYPE == "REAL" and os.getenv("CONFIRM_REAL") != "YES":
            log.error("Conta REAL sem CONFIRM_REAL=YES — abortando por segurança. Use PRACTICE.")
            return
        if not self.connect():
            return
        self._start_watchdog()

        log.info(f"START multi:{len(self.assets)} {','.join(self.assets)} | {cfg.STRATEGY} "
                 f"RSI({cfg.RSI_PERIOD}) {cfg.RSI_OVERSOLD}/{cfg.RSI_OVERBOUGHT} "
                 f"exit={int(cfg.RSI_REQUIRE_EXIT)} H1_EMA={cfg.HTF_EMA} | Kelly "
                 f"{cfg.KELLY_FRACTION}x teto {cfg.KELLY_MAX_RISK*100:.0f}% | max_concurrent={cfg.MAX_CONCURRENT}")
        errors = 0

        try:
            while True:
                try:
                    if self.stop():
                        break
                    if not self.ensure_connected():
                        time.sleep(60)
                        continue
                    self._write_status()
                    detail = self._fetch_detail()
                    if detail is None:
                        log.info("Sem detail de payout, aguardando.")
                        time.sleep(60)
                        continue
                    self._reconcile_pending()

                    # sinal manual tem prioridade (botao cockpit)
                    manual = self._check_manual()
                    if manual:
                        asset = manual["asset"]
                        payout = self.get_payout(asset, detail)
                        if payout < cfg.PAYOUT_MIN:
                            log.info(f"MANUAL {asset} ignorado: payout {payout:.2f} < mínimo.")
                        else:
                            stake, p, kfull = self._manual_stake(asset, payout, manual["stake"])
                            order = self._fire_buy(asset, manual["signal"], stake)
                            if order:
                                order.update({"signal": manual["signal"], "info": "MANUAL",
                                              "payout": payout, "p": p, "kfull": kfull})
                                self.pending.append(order)
                                self._save_pending()
                                if len(self.pending) > cfg.MAX_CONCURRENT:
                                    log.warning(f"MANUAL bypass cap ({len(self.pending)}/{cfg.MAX_CONCURRENT} pendentes).")
                        time.sleep(5)
                        continue

                    for asset in self.assets:
                        payout = self.get_payout(asset, detail)
                        if payout < cfg.PAYOUT_MIN:
                            continue
                        df = self.candles_df(asset, cfg.TIMEFRAME, cfg.CANDLE_COUNT)
                        if df is None or df.empty:
                            log.warning(f"Sem candles ({asset} M{cfg.EXPIRATION}) — aguardando.")
                            continue
                        candle_key = self._candle_key(df)
                        if candle_key == self.last_candle_key.get(asset):
                            continue
                        self.last_candle_key[asset] = candle_key
                        if candle_key.startswith("noclock:"):
                            log.warning(f"{asset}: coluna de tempo ausente nos candles — avaliando sem dedup por candle.")

                        df_h1 = None
                        if cfg.STRATEGY == "rsi_mtf_pullback":
                            df_h1 = self.candles_df(asset, cfg.HTF_TIMEFRAME, cfg.HTF_COUNT)
                            if df_h1 is None or df_h1.empty:
                                continue

                        signal = get_signal(cfg.STRATEGY, df, cfg, df_h1)
                        self.last_signal[asset] = signal
                        close_px = float(df["close"].iloc[-1])
                        if cfg.STRATEGY == "donchian_fade":
                            info: object = f"DC{cfg.DONCHIAN_N}"
                            n = cfg.DONCHIAN_N
                            hi = float(df["high"].iloc[-n - 1:-1].max())
                            lo = float(df["low"].iloc[-n - 1:-1].min())
                            detail_s = f"close={close_px:.2f} hi20={hi:.2f} lo20={lo:.2f}"
                        else:
                            info = round(float(rsi_series(df["close"], cfg.RSI_PERIOD).iloc[-1]), 1)
                            detail_s = f"close={close_px:.2f} RSI={info}"
                        self.last_payout[asset] = payout
                        self.last_check[asset] = f"{detail_s} signal={signal} payout={payout:.2f}"
                        log.info(f"[CHECK] {asset} {candle_key} {detail_s} -> {signal} (payout {payout:.2f})")
                        self._write_status()
                        if not signal:
                            continue
                        if len(self.pending) >= cfg.MAX_CONCURRENT:
                            log.info(f"SINAL {signal.upper()} {asset} ignorado: cap {cfg.MAX_CONCURRENT} pendentes atingido.")
                            continue

                        stake, p, kfull = self.calc_stake(asset, payout)
                        log.info(f"SINAL {signal.upper()} {asset} {info} payout={payout:.2f} "
                                 f"p={p:.2f} kelly={kfull:.3f} stake={stake:.2f}")
                        order = self._fire_buy(asset, signal, stake)
                        if order:
                            order.update({"signal": signal, "info": info,
                                          "payout": payout, "p": p, "kfull": kfull})
                            self.pending.append(order)
                            self._save_pending()
                    errors = 0
                    time.sleep(15)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    errors += 1
                    log.error(f"Erro no loop ({errors}): {e}")
                    time.sleep(min(60 * errors, 300))
        except KeyboardInterrupt:
            log.info("Interrompido pelo usuário.")
        finally:
            try:
                log.info(f"FIM Sessão {self.profit:.2f} | Saldo {self._safe_balance()}")
            except Exception:
                log.info(f"FIM Sessão {self.profit:.2f}")
