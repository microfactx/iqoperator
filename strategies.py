"""Estratégias para BTCUSD Binárias (M15 + RSI)."""
import pandas as pd


def rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))


def rsi_m15_signal(df: pd.DataFrame, period: int = 14,
                   overbought: float = 70, oversold: float = 30,
                   require_exit: bool = True) -> str | None:
    """RSI M15 reversão à média.
    - require_exit=True: CALL quando RSI sai de baixo p/ cima do oversold;
      PUT quando sai de cima p/ baixo do overbought (1 sinal por saída).
    - require_exit=False: CALL todo candle com RSI<oversold, PUT com RSI>overbought.
    Usa candle fechado (penúltimo se o último ainda está formando).
    """
    if len(df) < period + 3:
        return None

    rsi = rsi_series(df["close"], period)
    prev_rsi = float(rsi.iloc[-2])
    last_rsi = float(rsi.iloc[-1])

    if require_exit:
        if prev_rsi <= oversold < last_rsi:
            return "call"
        if prev_rsi >= overbought > last_rsi:
            return "put"
        return None
    if last_rsi < oversold:
        return "call"
    if last_rsi > overbought:
        return "put"
    return None

def rsi_momentum_signal(df: pd.DataFrame, period: int = 14,
                        overbought: float = 70, oversold: float = 30,
                        require_exit: bool = True) -> str | None:
    """RSI M15 continuação de tendência.
    - require_exit=True: CALL quando RSI rompe OB p/ cima; PUT quando rompe OS p/ baixo.
    - require_exit=False: CALL todo candle com RSI>OB, PUT com RSI<OS.
    """
    if len(df) < period + 3:
        return None

    rsi = rsi_series(df["close"], period)
    prev_rsi = float(rsi.iloc[-2])
    last_rsi = float(rsi.iloc[-1])

    if require_exit:
        if prev_rsi <= overbought < last_rsi:
            return "call"
        if prev_rsi >= oversold > last_rsi:
            return "put"
        return None
    if last_rsi > overbought:
        return "call"
    if last_rsi < oversold:
        return "put"
    return None

def rsi_momentum_trend_signal(df: pd.DataFrame, period: int = 14,
                              overbought: float = 70, oversold: float = 30,
                              require_exit: bool = True,
                              trend_span: int = 200) -> str | None:
    """Momentum só a favor da tendência: CALL exige close > EMA(trend_span),
    PUT exige close < EMA(trend_span)."""
    if len(df) < period + 3:
        return None

    sig = rsi_momentum_signal(df, period, overbought, oversold, require_exit)
    if not sig:
        return None
    trend = df["close"].ewm(span=trend_span, adjust=False).mean()
    last_close = float(df["close"].iloc[-1])
    last_ema = float(trend.iloc[-1])
    if sig == "call" and last_close <= last_ema:
        return None
    if sig == "put" and last_close >= last_ema:
        return None
    return sig


def rsi_mtf_pullback_signal(df_m15: pd.DataFrame, df_h1: pd.DataFrame,
                              period: int = 14,
                              overbought: float = 70, oversold: float = 30,
                              require_exit: bool = False,
                              htf_ema: int = 50,
                              htf_seconds: int = 3600) -> str | None:
    """Setup do backtest 1y: viés H1 + gatilho pullback RSI no M15.
    Regra idêntica à validada: usa a última barra H1 100% fechada antes da
    abertura do candle M15 de entrada (close_H1 <= from_M15). Sem lookahead."""
    if df_m15 is None or df_h1 is None or len(df_m15) < period + 3 or len(df_h1) < 3:
        return None

    h1_close = df_h1["close"]
    h1_ema = h1_close.ewm(span=htf_ema, adjust=False).mean()
    try:
        entry_from = float(df_m15["from"].iloc[-1])
        h1_from = df_h1["from"].astype(float)
        eligible = df_h1[(h1_from + htf_seconds <= entry_from).to_numpy()]
        if eligible.empty:
            return None
        ref = eligible.index[-1]
        bias_long = float(h1_close.loc[ref]) > float(h1_ema.loc[ref])
        bias_short = float(h1_close.loc[ref]) < float(h1_ema.loc[ref])
    except (KeyError, ValueError, IndexError):
        # fallback conservador sem timestamp: pula as 2 últimas barras H1
        if len(df_h1) < 4:
            return None
        bias_long = float(h1_close.iloc[-3]) > float(h1_ema.iloc[-3])
        bias_short = float(h1_close.iloc[-3]) < float(h1_ema.iloc[-3])

    rsi = rsi_series(df_m15["close"], period)
    prev_rsi = float(rsi.iloc[-2])
    last_rsi = float(rsi.iloc[-1])

    if require_exit:
        if bias_long and prev_rsi <= oversold < last_rsi:
            return "call"
        if bias_short and prev_rsi >= overbought > last_rsi:
            return "put"
        return None
    if bias_long and last_rsi < oversold:
        return "call"
    if bias_short and last_rsi > overbought:
        return "put"
    return None


def donchian_fade_signal(df: pd.DataFrame, n: int = 20) -> str | None:
    """Fade de rompimento Donchian: close acima da máxima dos últimos n
    candles (excluindo o atual) -> PUT; abaixo da mínima -> CALL.
    Regra idêntica à validada (IS+OOS+ano fresco). df.iloc[-1] = candle fechado."""
    if len(df) < n + 2:
        return None
    high = df.get("high", df.get("max"))
    low = df.get("low", df.get("min"))
    if high is None or low is None:
        return None
    hi = float(high.iloc[-n - 1:-1].max())
    lo = float(low.iloc[-n - 1:-1].min())
    close = float(df["close"].iloc[-1])
    if close > hi:
        return "put"
    if close < lo:
        return "call"
    return None


def ema_cross_signal(df: pd.DataFrame, fast: int = 9, slow: int = 21,
                      rsi_period: int = 14, overbought: float = 70,
                      oversold: float = 30) -> str | None:
    """Retorna 'call', 'put' ou None.
    Regra: cruzamento EMA fast/slow + filtro RSI (evita sobrecomprado/sobrevendido contra a entrada).
    df precisa ter coluna 'close'.
    """
    if len(df) < slow + 3:
        return None

    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

    # RSI simples sem depender de lib externa
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / rsi_period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / rsi_period, adjust=False).mean()
    rsi = 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))
    last_rsi = float(rsi.iloc[-1])

    prev_diff = float(ema_fast.iloc[-2] - ema_slow.iloc[-2])
    last_diff = float(ema_fast.iloc[-1] - ema_slow.iloc[-1])

    # Cruzou pra cima -> call (se não sobrecomprado)
    if prev_diff <= 0 < last_diff and last_rsi < overbought:
        return "call"
    # Cruzou pra baixo -> put (se não sobrevendido)
    if prev_diff >= 0 > last_diff and last_rsi > oversold:
        return "put"
    return None


def get_signal(strategy: str, df: pd.DataFrame, cfg, df_htf: pd.DataFrame | None = None) -> str | None:
    if strategy == "donchian_fade":
        return donchian_fade_signal(df, n=cfg.DONCHIAN_N)
    if strategy == "rsi_mtf_pullback":
        return rsi_mtf_pullback_signal(
            df, df_htf, period=cfg.RSI_PERIOD,
            overbought=cfg.RSI_OVERBOUGHT,
            oversold=cfg.RSI_OVERSOLD,
            require_exit=cfg.RSI_REQUIRE_EXIT,
            htf_ema=cfg.HTF_EMA,
            htf_seconds=cfg.HTF_TIMEFRAME,
        )
    if strategy == "rsi_m15":
        return rsi_m15_signal(
            df, period=cfg.RSI_PERIOD,
            overbought=cfg.RSI_OVERBOUGHT,
            oversold=cfg.RSI_OVERSOLD,
            require_exit=cfg.RSI_REQUIRE_EXIT,
        )
    if strategy == "rsi_momentum_trend":
        return rsi_momentum_trend_signal(
            df, period=cfg.RSI_PERIOD,
            overbought=cfg.RSI_OVERBOUGHT,
            oversold=cfg.RSI_OVERSOLD,
            require_exit=cfg.RSI_REQUIRE_EXIT,
            trend_span=cfg.TREND_EMA,
        )
    if strategy == "rsi_momentum":
        return rsi_momentum_signal(
            df, period=cfg.RSI_PERIOD,
            overbought=cfg.RSI_OVERBOUGHT,
            oversold=cfg.RSI_OVERSOLD,
            require_exit=cfg.RSI_REQUIRE_EXIT,
        )
    if strategy == "ema_cross":
        return ema_cross_signal(
            df, fast=cfg.EMA_FAST, slow=cfg.EMA_SLOW,
            rsi_period=cfg.RSI_PERIOD,
            overbought=cfg.RSI_OVERBOUGHT,
            oversold=cfg.RSI_OVERSOLD,
        )
    return None
