"""Robô IQOption DEMO - Binárias BTCUSD | MTF pullback (H1 + RSI M15) + Kelly 2%."""
import csv
import json
import logging
import os
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


class Bot:
    def __init__(self):
        self.api = IQ_Option(cfg.EMAIL, cfg.PASSWORD)
        self.asset = cfg.ASSET
        self.profit = 0.0
        self.buys_attempted = 0
        self.buys_rejected = 0
        self.last_signal = None
        self.last_payout = None
        self.last_candle_key = None
        self.last_check = None
        self.history: deque[bool] = deque(maxlen=cfg.KELLY_LOOKBACK)
        self.martingale_step = 0
        self.current_amount = cfg.AMOUNT
        self._trade_log_init()

    def _trade_log_init(self):
        if not os.path.exists(cfg.TRADE_LOG):
            os.makedirs(os.path.dirname(cfg.TRADE_LOG) or ".", exist_ok=True)
            with open(cfg.TRADE_LOG, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(
                    ["time", "signal", "info", "payout", "winrate",
                     "kelly", "stake", "profit", "balance"])

    def _trade_log(self, row: list):
        with open(cfg.TRADE_LOG, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        # sem disco no Railway: espelha no dataset HF (se HF_TOKEN + HF_DATASET_REPO setados)
        sync_file(cfg.TRADE_LOG)

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

    def candles_df(self, timeframe: int, count: int) -> pd.DataFrame | None:
        try:
            candles = self.api.get_candles(self.asset, timeframe, count, time.time())
        except Exception as e:
            log.warning(f"get_candles falhou {self.asset}: {e}")
            return None
        if not candles:
            return None
        df = pd.DataFrame(candles)
        df = df.rename(columns={"max": "high", "min": "low"})
        for c in ("high", "low", "close", "open"):
            if c not in df.columns:
                df[c] = df.get("close", 0)
        return df

    def get_payout(self) -> float:
        try:
            detail = self.api.get_binary_option_detail()
            v = detail.get(self.asset) if isinstance(detail, dict) else None
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
            log.warning(f"payout fallback: {e}")
        return cfg.KELLY_PAYOUT_DEFAULT

    def calc_stake(self, payout: float) -> tuple[float, float, float]:
        balance = float(self.api.get_balance() or 0)
        p = empirical_winrate(list(self.history), cfg.KELLY_PRIOR,
                              prior_weight=cfg.KELLY_PRIOR_WEIGHT)
        if cfg.USE_KELLY:
            stake, kfull = kelly_fraction_stake(
                balance, payout, p, fraction=cfg.KELLY_FRACTION,
                max_risk=cfg.KELLY_MAX_RISK, min_amount=cfg.KELLY_MIN)
            return stake, p, kfull
        return round(self.current_amount, 2), p, 0.0

    def _wait_result(self, order_id, timeout: float) -> float | None:
        """Aguarda o resultado com deadline; heartbeat segue vivo durante a espera."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ok, data = self.api.get_betinfo(order_id)
            except Exception as e:
                log.warning(f"get_betinfo exceção id={order_id}: {e}")
                time.sleep(10)
                continue
            if ok and data:
                try:
                    node = data["result"]["data"][str(order_id)]
                except KeyError:
                    time.sleep(5)
                    continue
                if node.get("win") not in ("", None):
                    try:
                        return float(node["profit"]) - float(node["deposit"])
                    except (KeyError, TypeError, ValueError):
                        return None
            self.last_check = f"aguardando resultado id={order_id}"
            self._write_status()
            time.sleep(5)
        return None

    def trade(self, action: str, stake: float) -> float | None:
        self.buys_attempted += 1
        try:
            balance_before = float(self.api.get_balance() or 0)
        except Exception:
            balance_before = 0.0
        ok, order_id = self.api.buy(stake, self.asset, action, cfg.EXPIRATION)
        if not ok:
            self.buys_rejected += 1
            log.error(f"Buy rejeitado ({self.buys_rejected}/{self.buys_attempted}): {order_id} (ativo={self.asset})")
            return None
        log.info(f"TRADE {action.upper()} {self.asset} M{cfg.EXPIRATION} stake={stake} id={order_id}")
        try:
            profit = self._wait_result(order_id, cfg.EXPIRATION * 60 + 180)
            if profit is not None:
                return profit
            # deadline sem resposta: estima via delta de saldo (não trava o bot)
            try:
                balance_now = float(self.api.get_balance() or 0)
                est = round(balance_now - balance_before, 2)
            except Exception:
                est = 0.0
            log.warning(f"RESULT_TIMEOUT id={order_id} — sem betinfo; profit estimado via saldo: {est:+.2f}")
            return est
        except Exception as e:
            log.error(f"check_win falhou id={order_id}: {e}")
            return 0.0

    def update_result(self, signal: str, info: object, payout: float,
                      p: float, kfull: float, stake: float, profit: float):
        self.profit += profit
        won = profit > 0
        self.history.append(won)
        balance = self.api.get_balance()
        tag = "WIN" if won else "LOSS"
        wr = empirical_winrate(list(self.history), cfg.KELLY_PRIOR,
                               prior_weight=cfg.KELLY_PRIOR_WEIGHT)
        log.info(f"{tag} {profit:+.2f} | Sessão {self.profit:+.2f} | saldo {balance} | wr {wr:.2f}")
        self._trade_log([datetime.now().isoformat(timespec="seconds"), signal,
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
            os.makedirs(os.path.dirname(cfg.BOT_STATUS) or ".", exist_ok=True)
            import json
            with open(cfg.BOT_STATUS, "w", encoding="utf-8") as f:
                json.dump({
                    "last_tick": datetime.now(timezone.utc).isoformat(),
                    "asset": self.asset,
                    "balance": self.api.get_balance() if hasattr(self, 'api') else None,
                    "balance_type": cfg.BALANCE_TYPE,
                    "strategy": cfg.STRATEGY,
                    "profit_session": round(self.profit, 2),
                    "trades": len(self.history),
                    "winrate": round(empirical_winrate(list(self.history), cfg.KELLY_PRIOR, prior_weight=cfg.KELLY_PRIOR_WEIGHT), 4),
                    "buys_attempted": self.buys_attempted,
                    "buys_rejected": self.buys_rejected,
                    "last_payout": self.last_payout,
                    "last_signal": self.last_signal,
                    "last_candle_key": self.last_candle_key,
                    "last_check": self.last_check,
                }, f)
        except Exception:
            pass

    def _check_manual(self) -> str | None:
        try:
            if not os.path.exists(cfg.MANUAL_SIGNAL):
                return None
            import json
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
            log.info(f"MANUAL {sig.upper()} solicitado via cockpit")
            return sig
        except Exception as e:
            log.warning(f"manual check falhou: {e}")
            return None

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

        log.info(f"START {self.asset} | {cfg.STRATEGY} RSI({cfg.RSI_PERIOD}) "
                 f"{cfg.RSI_OVERSOLD}/{cfg.RSI_OVERBOUGHT} exit={int(cfg.RSI_REQUIRE_EXIT)} "
                 f"H1_EMA={cfg.HTF_EMA} | Kelly {cfg.KELLY_FRACTION}x teto {cfg.KELLY_MAX_RISK*100:.0f}%")
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
                    payout = self.get_payout()
                    if payout < cfg.PAYOUT_MIN:
                        log.info(f"Payout {payout:.2f} < mínimo, aguardando.")
                        time.sleep(60)
                        continue

                    # sinal manual tem prioridade (botao cockpit)
                    manual = self._check_manual()
                    if manual:
                        stake, p, kfull = self.calc_stake(payout)
                        profit = self.trade(manual, stake)
                        if profit is None:
                            time.sleep(5)
                            continue
                        self.update_result(manual, "MANUAL", payout, p, kfull, stake, profit)
                        time.sleep(5)
                        continue

                    df = self.candles_df(cfg.TIMEFRAME, cfg.CANDLE_COUNT)
                    if df is None or df.empty:
                        log.warning(f"Sem candles ({self.asset} M{cfg.EXPIRATION}) — aguardando.")
                        time.sleep(15)
                        continue
                    candle_key = self._candle_key(df)
                    if candle_key == self.last_candle_key:
                        time.sleep(15)
                        continue
                    self.last_candle_key = candle_key
                    if candle_key.startswith("noclock:"):
                        log.warning("Coluna de tempo ausente nos candles — avaliando sem dedup por candle.")

                    df_h1 = None
                    if cfg.STRATEGY == "rsi_mtf_pullback":
                        df_h1 = self.candles_df(cfg.HTF_TIMEFRAME, cfg.HTF_COUNT)
                        if df_h1 is None or df_h1.empty:
                            time.sleep(15)
                            continue

                    signal = get_signal(cfg.STRATEGY, df, cfg, df_h1)
                    self.last_signal = signal
                    close_px = float(df["close"].iloc[-1])
                    if cfg.STRATEGY == "donchian_fade":
                        info: object = f"DC{cfg.DONCHIAN_N}"
                        n = cfg.DONCHIAN_N
                        hi = float(df["high"].iloc[-n - 1:-1].max())
                        lo = float(df["low"].iloc[-n - 1:-1].min())
                        detail = f"close={close_px:.2f} hi20={hi:.2f} lo20={lo:.2f}"
                    else:
                        info = round(float(rsi_series(df["close"], cfg.RSI_PERIOD).iloc[-1]), 1)
                        detail = f"close={close_px:.2f} RSI={info}"
                    self.last_payout = payout
                    self.last_check = f"{detail} signal={signal} payout={payout:.2f}"
                    log.info(f"[CHECK] {candle_key} {detail} -> {signal} (payout {payout:.2f})")
                    self._write_status()
                    if not signal:
                        time.sleep(15)
                        continue

                    stake, p, kfull = self.calc_stake(payout)
                    log.info(f"SINAL {signal.upper()} {info} payout={payout:.2f} "
                             f"p={p:.2f} kelly={kfull:.3f} stake={stake:.2f}")
                    profit = self.trade(signal, stake)
                    if profit is None:
                        time.sleep(30)
                        continue
                    self.update_result(signal, info, payout, p, kfull, stake, profit)
                    errors = 0
                    time.sleep(5)
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
                log.info(f"FIM Sessão {self.profit:.2f} | Saldo {self.api.get_balance()}")
            except Exception:
                log.info(f"FIM Sessão {self.profit:.2f}")
