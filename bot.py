"""Robô IQOption DEMO - Binárias BTCUSD | MTF pullback (H1 + RSI M15) + Kelly 2%."""
import csv
import logging
import os
import time
from collections import deque
from datetime import datetime
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
        self.profit = 0.0
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
            candles = self.api.get_candles(cfg.ASSET, timeframe, count, time.time())
        except Exception as e:
            log.warning(f"get_candles falhou: {e}")
            return None
        if not candles:
            return None
        df = pd.DataFrame(candles)
        # IQOption usa max/min; normaliza para high/low/close/open/from
        rename = {"max": "high", "min": "low"}
        df = df.rename(columns=rename)
        # garante colunas essenciais
        for c in ("high", "low", "close", "open"):
            if c not in df.columns:
                df[c] = df.get("close", 0)
        return df

    def get_payout(self) -> float:
        try:
            detail = self.api.get_binary_option_detail()
            for key in (cfg.ASSET, f"{cfg.ASSET}-OTC"):
                if isinstance(detail, dict) and key in detail:
                    v = detail[key]
                    if isinstance(v, dict):
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

    def trade(self, action: str, stake: float) -> float:
        ok, order_id = self.api.buy(stake, cfg.ASSET, action, cfg.EXPIRATION)
        if not ok:
            log.error(f"Buy rejeitado: {order_id}")
            return 0.0
        log.info(f"TRADE {action.upper()} {cfg.ASSET} M{cfg.EXPIRATION} stake={stake} id={order_id}")
        try:
            return float(self.api.check_win_v2(order_id))
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

        log.info(f"START {cfg.ASSET} | {cfg.STRATEGY} RSI({cfg.RSI_PERIOD}) "
                 f"{cfg.RSI_OVERSOLD}/{cfg.RSI_OVERBOUGHT} exit={int(cfg.RSI_REQUIRE_EXIT)} "
                 f"H1_EMA={cfg.HTF_EMA} | Kelly {cfg.KELLY_FRACTION}x teto {cfg.KELLY_MAX_RISK*100:.0f}%")
        last_candle_time = 0
        errors = 0

        try:
            while True:
                try:
                    if self.stop():
                        break
                    if not self.ensure_connected():
                        time.sleep(60)
                        continue
                    payout = self.get_payout()
                    if payout < cfg.PAYOUT_MIN:
                        log.info(f"Payout {payout:.2f} < mínimo, aguardando.")
                        time.sleep(60)
                        continue

                    df = self.candles_df(cfg.TIMEFRAME, cfg.CANDLE_COUNT)
                    if df is None or df.empty:
                        time.sleep(15)
                        continue
                    candle_time = int(df.iloc[-1].get("from", 0) or 0)
                    if candle_time == last_candle_time:
                        time.sleep(15)
                        continue
                    last_candle_time = candle_time

                    df_h1 = None
                    if cfg.STRATEGY == "rsi_mtf_pullback":
                        df_h1 = self.candles_df(cfg.HTF_TIMEFRAME, cfg.HTF_COUNT)
                        if df_h1 is None or df_h1.empty:
                            time.sleep(15)
                            continue

                    signal = get_signal(cfg.STRATEGY, df, cfg, df_h1)
                    if cfg.STRATEGY == "donchian_fade":
                        info: object = f"DC{cfg.DONCHIAN_N}"
                    else:
                        info = round(float(rsi_series(df["close"], cfg.RSI_PERIOD).iloc[-1]), 1)
                    if not signal:
                        time.sleep(15)
                        continue

                    stake, p, kfull = self.calc_stake(payout)
                    log.info(f"SINAL {signal.upper()} {info} payout={payout:.2f} "
                             f"p={p:.2f} kelly={kfull:.3f} stake={stake:.2f}")
                    profit = self.trade(signal, stake)
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
