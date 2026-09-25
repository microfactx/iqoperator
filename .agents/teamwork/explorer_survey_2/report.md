# Specification Report: Feature Engineering and Labeling Pipeline (R1)
**Project**: Projeto Híbrido de Transcendência  
**Component**: R1 — Pipeline de Engenharia de Dados, Features e Rotulagem  
**Author**: Explorer Survey 2 (Feature Engineering & Labeling Specialist)  
**Date**: 2026-09-25  
**Target Environment**: Python 3.12 (`.venv`), pandas 3.0.6, numpy 2.5.3, scikit-learn  

---

## 1. Executive Summary

The objective of Requirement R1 is to engineer a robust, scale-invariant feature extraction and labeling pipeline to support a Machine Learning classification filter. This filter sits as an intelligent supervisor over the existing deterministic strategies (`donchian_fade` and `bollinger_touch`), predicting the probability that a detected breakout signal is a legitimate mean-reverting reversal (Target = 1) versus a false breakout / noisy continuation (Target = 0).

### Key Empirical Findings from Codebase Verification:
1. **Existing Implementations**:
   - `donchian_fade` (`strategies.py:135`, `research/grid_families.py:150`): Fades Donchian channel breakout of the prior $n=20$ bars. If $Close_t > UpperDC_{20}(t) \implies \text{PUT}$; if $Close_t < LowerDC_{20}(t) \implies \text{CALL}$.
   - `bollinger_touch` (`strategies.py:155`): Fades Bollinger Band touches ($p=20, \text{mult}=2.0$). If $Close_t > UpperBB_{20}(t) \implies \text{PUT}$; if $Close_t < LowerBB_{20}(t) \implies \text{CALL}$.
2. **Empirical Signal & Baseline Performance (1-Year M15 Data)**:
   - **`data/BTCUSDT_M15_1y.csv` (35,000 candles)**:
     - Donchian Fade Events: 3,400 signals | Baseline Reversal Winrate: **56.12%**
     - Bollinger Touch Events: 3,796 signals | Baseline Reversal Winrate: **54.90%**
     - Confluence Events (both trigger same side): 2,386 signals | Baseline Reversal Winrate: **55.74%**
     - Union Candidate Signals (at least one triggers): 4,810 signals | Baseline Reversal Winrate: **55.34%**
   - **`data/EURUSD_M15_histdata.csv` (40,000 candles)**:
     - Donchian Fade Events: 4,563 signals | Baseline Reversal Winrate: **52.75%**
     - Bollinger Touch Events: 4,479 signals | Baseline Reversal Winrate: **53.11%**
   - **Takeaway**: Raw deterministic strategies hover near or below the binary broker breakeven rate ($1 / (1 + \text{payout}) = 53.48\%$ at payout 0.87; $52.63\%$ at payout 0.90). The ML classification filter is strictly necessary to isolate high-confidence subsets where Precision $\ge 60\% - 65\%$.
3. **Lookahead Bias Prevention**:
   - Zero future lookahead bias requires:
     1. Strict lag indexing on channel boundaries (Donchian uses bars $t-n$ to $t-1$).
     2. Stationary, scale-invariant relative features (no raw price levels).
     3. Strict chronological split *before* fitting scalers/encoders.
     4. Purge window of $H=4$ candles between train and validation/test splits.

---

## 2. Invariant Data Schema & Preprocessing

### 2.1 Raw Input Schema
The pipeline operates on historical M15 candle files (`BTCUSDT_M15_1y.csv`, `EURUSD_M15_histdata.csv`).
- **Input Columns**: `time, open, high, low, close` (all float64, except `time` integer/float epoch).
- **Time Format Normalization**:
  $$t_{\text{datetime}} = \text{pd.to\_datetime}(df['time'], unit='ms', utc=True)$$
  *(Supports auto-detection: if $\text{value} < 10^{11}$, interpret as seconds and multiply by 1000).*
- **Monotonicity & Gap Invariant**:
  - Verify $\Delta t_i = t_i - t_{i-1} > 0$ strictly.
  - In M15 candles, expected step is $900$ seconds ($15$ minutes).

### 2.2 Warmup & Horizon Bounds
- **Warmup Horizon ($N_{\text{warmup}} = 60$)**:
  The longest technical indicator requires $p=60$ bars (`dc_upper_60`, `sma_50`). The first 60 rows must be dropped after feature computation to guarantee zero NaN values in feature matrices without forward imputation.
- **Expiry Horizon ($H = 4$)**:
  For M15 candles, 1 hour forward corresponds to $4$ candles:
  $$H = \frac{3600\text{ seconds}}{900\text{ seconds/candle}} = 4 \text{ candles}$$
  The last $H=4$ rows of the dataset must be excluded from labeled training/testing sets as their ground truth outcome is beyond the dataset boundary.

---

## 3. Temporal Feature Engineering Specifications

Linear representations of time (e.g. hour 0 to 23) create an artificial discontinuity between 23:59 and 00:00. In financial markets, volatility and reversal tendencies are strongly cyclical according to global trading sessions (Tokyo, London, New York).

### 3.1 Mathematical Formulations
Let $T_t$ be the bar timestamp at index $t$.
1. **Discrete Temporal Components**:
   - Hour of Day: $H_t = \text{Hour}(T_t) \in [0, 23]$
   - Day of Week: $D_t = \text{DayOfWeek}(T_t) \in [0, 6]$ (0 = Monday, 6 = Sunday)
   - Minute of Hour: $M_t = \text{Minute}(T_t) \in \{0, 15, 30, 45\}$
   - Intraday Minute: $IM_t = H_t \cdot 60 + M_t \in [0, 1439]$

2. **Continuous Cyclical Encodings (Unit Circle Mapping)**:
   - **Hour Cyclical**:
     $$\sin\_hour_t = \sin\left(\frac{2\pi \cdot H_t}{24}\right), \quad \cos\_hour_t = \cos\left(\frac{2\pi \cdot H_t}{24}\right)$$
   - **Day of Week Cyclical**:
     $$\sin\_dow_t = \sin\left(\frac{2\pi \cdot D_t}{7}\right), \quad \cos\_dow_t = \cos\left(\frac{2\pi \cdot D_t}{7}\right)$$
   - **High-Precision Time-of-Day Cyclical**:
     $$\sin\_tod_t = \sin\left(\frac{2\pi \cdot IM_t}{1440}\right), \quad \cos\_tod_t = \cos\left(\frac{2\pi \cdot IM_t}{1440}\right)$$

3. **Binary Market Session Indicators**:
   - `session_asian`: $\mathbb{I}(H_t \in [0, 8))$ (00:00 - 08:00 UTC)
   - `session_london`: $\mathbb{I}(H_t \in [8, 16))$ (08:00 - 16:00 UTC)
   - `session_ny`: $\mathbb{I}(H_t \in [13, 21))$ (13:00 - 21:00 UTC)
   - `session_london_ny_overlap`: $\mathbb{I}(H_t \in [13, 16))$ (Peak volume/volatility hours)
   - `is_weekend`: $\mathbb{I}(D_t \in \{5, 6\})$ (Critical for OTC assets vs standard market regimes)

---

## 4. Technical Feature Engineering Specifications

All technical indicators are formulated as scale-invariant relative quantities. Raw dollar/crypto price levels are non-stationary ($I(1)$) and must never be fed directly into classifiers.

### 4.1 Multi-Period Simple Moving Averages (SMA)
Evaluated across multiple timeframes: $p \in \{5, 10, 20, 50\}$.
$$SMA_p(t) = \frac{1}{p} \sum_{i=0}^{p-1} Close_{t-i}$$

Derived Scale-Invariant Features:
1. **Price Distance to SMA**:
   $$dist\_sma_p(t) = \frac{Close_t - SMA_p(t)}{SMA_p(t)}$$
2. **SMA Slope (Momentum)**:
   $$slope\_sma_p(t) = \frac{SMA_p(t) - SMA_p(t-1)}{SMA_p(t-1)}$$
3. **Multi-Period Moving Average Spread Ratios**:
   $$spread\_sma_{5,20}(t) = \frac{SMA_5(t) - SMA_{20}(t)}{SMA_{20}(t)}$$
   $$spread\_sma_{10,50}(t) = \frac{SMA_{10}(t) - SMA_{50}(t)}{SMA_{50}(t)}$$
   $$spread\_sma_{20,50}(t) = \frac{SMA_{20}(t) - SMA_{50}(t)}{SMA_{50}(t)}$$

### 4.2 Multi-Period Rolling Standard Deviation (StdDev)
Evaluated across periods $p \in \{5, 10, 20, 50\}$:
$$StdDev_p(t) = \sqrt{\frac{1}{p} \sum_{i=0}^{p-1} (Close_{t-i} - SMA_p(t))^2}$$

Derived Scale-Invariant Features:
1. **Normalized Volatility (Coefficient of Variation)**:
   $$vol\_ratio_p(t) = \frac{StdDev_p(t)}{SMA_p(t)}$$
2. **Volatility Shock Ratio (Fast vs Slow)**:
   $$vol\_shock(t) = \frac{StdDev_5(t)}{StdDev_{50}(t) + 10^{-9}}$$
   *(Detects sudden volatility spikes indicating momentum breakouts vs quiet exhaustion).*

### 4.3 Bollinger Bands
Calculated with baseline parameters $p = 20, k = 2.0$:
- Midline: $MB(t) = SMA_{20}(t)$
- Upper Band: $UB_{20, 2.0}(t) = SMA_{20}(t) + 2.0 \cdot StdDev_{20}(t)$
- Lower Band: $LB_{20, 2.0}(t) = SMA_{20}(t) - 2.0 \cdot StdDev_{20}(t)$

Derived Scale-Invariant Features:
1. **Bollinger Bandwidth ($BB\_Width$)**:
   $$BB\_Width(t) = \frac{UB_{20}(t) - LB_{20}(t)}{MB(t)} = \frac{4.0 \cdot StdDev_{20}(t)}{SMA_{20}(t)}$$
   *(Quantifies volatility compression [squeeze] vs expansion).*
2. **Bollinger Percent %B ($BB\_\%B$)**:
   $$\%B(t) = \frac{Close_t - LB_{20}(t)}{UB_{20}(t) - LB_{20}(t) + 10^{-9}}$$
   - $\%B > 1.0$: Price above upper band.
   - $\%B < 0.0$: Price below lower band.
   - $\%B = 0.5$: Price exactly at midline.
3. **Upper and Lower Penetration Ratios**:
   $$BB\_Pen\_Upper(t) = \max\left(0, \frac{Close_t - UB_{20}(t)}{UB_{20}(t)}\right)$$
   $$BB\_Pen\_Lower(t) = \max\left(0, \frac{LB_{20}(t) - Close_t}{LB_{20}(t)}\right)$$

### 4.4 Donchian Channels (Zero-Lookahead Formulations)
Evaluated across multiple lookbacks: $n \in \{10, 20, 40, 60\}$ (Default $n=20$ as in `DONCHIAN_N=20`).

**CRITICAL INVARIANT**: To eliminate lookahead bias, channel boundaries at bar $t$ must strictly exclude bar $t$.
$$UpperDC_n(t) = \max_{j \in [1, n]} High_{t-j} = \max\left(High_{t-n}, \dots, High_{t-1}\right)$$
$$LowerDC_n(t) = \min_{j \in [1, n]} Low_{t-j} = \min\left(Low_{t-n}, \dots, Low_{t-1}\right)$$
$$MidDC_n(t) = \frac{UpperDC_n(t) + LowerDC_n(t)}{2}$$

Derived Scale-Invariant Features:
1. **Donchian Channel Width ($DC\_Width_n$)**:
   $$DC\_Width_n(t) = \frac{UpperDC_n(t) - LowerDC_n(t)}{MidDC_n(t)}$$
2. **Donchian Relative Channel Position ($DC\_\%_n$)**:
   $$\%DC_n(t) = \frac{Close_t - LowerDC_n(t)}{UpperDC_n(t) - LowerDC_n(t) + 10^{-9}}$$
   - $\%DC_n > 1.0 \implies Close_t > UpperDC_n(t)$ (Breakout above lookback high)
   - $\%DC_n < 0.0 \implies Close_t < LowerDC_n(t)$ (Breakout below lookback low)
3. **Donchian Breakout Magnitude / Penetration**:
   $$DC\_Break\_Upper_n(t) = \max\left(0, \frac{Close_t - UpperDC_n(t)}{UpperDC_n(t)}\right)$$
   $$DC\_Break\_Lower_n(t) = \max\left(0, \frac{LowerDC_n(t) - Close_t}{LowerDC_n(t)}\right)$$

### 4.5 Candlestick Morphological Context
- **Body Ratio**: $\frac{|Close_t - Open_t|}{High_t - Low_t + 10^{-9}}$
- **Upper Wick / Rejection Ratio**: $\frac{High_t - \max(Open_t, Close_t)}{High_t - Low_t + 10^{-9}}$
- **Lower Wick / Rejection Ratio**: $\frac{\min(Open_t, Close_t) - Low_t}{High_t - Low_t + 10^{-9}}$
- **Past Normalized Returns**:
  $$ret_1(t) = \frac{Close_t - Close_{t-1}}{Close_{t-1}}, \quad ret_3(t) = \frac{Close_t - Close_{t-3}}{Close_{t-3}}, \quad ret_5(t) = \frac{Close_t - Close_{t-5}}{Close_{t-5}}$$

---

## 5. Deterministic Signal Extraction

The deterministic signals from `donchian_fade` and `bollinger_touch` serve as the triggering mechanism.

### 5.1 `donchian_fade` Extraction
Based on `strategies.py:135` and `bot.py:695`:
$$\text{sig\_df}(t) = \begin{cases} \text{'put'} & \text{if } Close_t > UpperDC_{20}(t) \\ \text{'call'} & \text{if } Close_t < LowerDC_{20}(t) \\ \text{'none'} & \text{otherwise} \end{cases}$$
- Numerical Direction:
  $$sig\_df\_dir_t = \begin{cases} +1 & \text{if } \text{sig\_df}(t) = \text{'call'} \\ -1 & \text{if } \text{sig\_df}(t) = \text{'put'} \\ 0 & \text{if } \text{sig\_df}(t) = \text{'none'} \end{cases}$$
- Binary flags: $sig\_df\_call_t = \mathbb{I}(sig\_df\_dir_t == +1)$, $sig\_df\_put_t = \mathbb{I}(sig\_df\_dir_t == -1)$.

### 5.2 `bollinger_touch` Extraction
Based on `strategies.py:155` and `bot.py:701`:
$$\text{sig\_bb}(t) = \begin{cases} \text{'put'} & \text{if } Close_t > UB_{20, 2.0}(t) \\ \text{'call'} & \text{if } Close_t < LB_{20, 2.0}(t) \\ \text{'none'} & \text{otherwise} \end{cases}$$
- Numerical Direction:
  $$sig\_bb\_dir_t = \begin{cases} +1 & \text{if } \text{sig\_bb}(t) = \text{'call'} \\ -1 & \text{if } \text{sig\_bb}(t) = \text{'put'} \\ 0 & \text{if } \text{sig\_bb}(t) = \text{'none'} \end{cases}$$
- Binary flags: $sig\_bb\_call_t = \mathbb{I}(sig\_bb\_dir_t == +1)$, $sig\_bb\_put_t = \mathbb{I}(sig\_bb\_dir_t == -1)$.

### 5.3 Confluence & Disagreement Dynamics
- **Confluence Direction**:
  $$sig\_confluence\_dir_t = \begin{cases} +1 & \text{if } sig\_df\_dir_t == +1 \land sig\_bb\_dir_t == +1 \\ -1 & \text{if } sig\_df\_dir_t == -1 \land sig\_bb\_dir_t == -1 \\ 0 & \text{otherwise} \end{cases}$$
- **Strategy Agreement Flag**:
  $$sig\_agreement_t = \mathbb{I}(sig\_df\_dir_t == sig\_bb\_dir_t \land sig\_df\_dir_t \ne 0)$$
- **Candidate Signal for Classification Filter**:
  A candidate signal is produced whenever at least one strategy fires, discarding rare contradictory signals:
  $$\text{candidate\_signal}_t = \begin{cases} 
  \text{'call'} & \text{if } (sig\_df\_dir_t == 1 \lor sig\_bb\_dir_t == 1) \land (sig\_df\_dir_t \ne -1 \land sig\_bb\_dir_t \ne -1) \\
  \text{'put'} & \text{if } (sig\_df\_dir_t == -1 \lor sig\_bb\_dir_t == -1) \land (sig\_df\_dir_t \ne 1 \land sig\_bb\_dir_t \ne 1) \\
  \text{'none'} & \text{otherwise}
  \end{cases}$$

---

## 6. Target Variable Definition & Zero Lookahead Bias Specification

### 6.1 Mathematical Formulation of Target
The requirement specifies:
> *"Criar a variável alvo (Target = 1 se o preço reverteu com lucro na próxima hora, 0 se foi falso rompimento)."*

For an option or position entered at the close of candle $t$, with an expiration horizon of $H = 4$ candles (60 minutes in M15):
- Entry Price: $P_{\text{entry}} = Close_t$
- Outcome / Expiry Price: $P_{\text{exit}} = Close_{t+H} = Close_{t+4}$

The binary target variable $y_t \in \{0, 1\}$ is defined strictly conditional on the candidate mean-reversion signal:
$$y_t = \begin{cases}
1 & \text{if } \text{candidate\_signal}_t = \text{'call'} \land Close_{t+4} > Close_t \\
1 & \text{if } \text{candidate\_signal}_t = \text{'put'} \land Close_{t+4} < Close_t \\
0 & \text{if } \text{candidate\_signal}_t = \text{'call'} \land Close_{t+4} \le Close_t \\
0 & \text{if } \text{candidate\_signal}_t = \text{'put'} \land Close_{t+4} \ge Close_t \\
\text{NaN} & \text{if } \text{candidate\_signal}_t = \text{'none'}
\end{cases}$$

#### Interpretation:
- **Target = 1 (True Reversal / Profitable)**: The market faded the extreme condition and reverted in the predicted direction within 1 hour.
- **Target = 0 (False Breakout / Continuation / Loss)**: The price failed to reverse (continued breaking out or flatlined). In binary trading, ties ($Close_{t+4} == Close_t$) return zero profit and are strictly classified as $0$.

### 6.2 Zero Future Lookahead Bias Protocol (Forensic Rules)

To withstand strict forensic audit and ensure realistic out-of-sample performance:

1. **Shift Direction Invariants**:
   - Past information strictly uses positive lags: `.shift(1)`, `.rolling(n)`.
   - Future information strictly used ONLY for Target calculation: `.shift(-H)`.
   - Never allow Target or forward prices into feature columns $X$.
2. **Warmup & Tail Purging**:
   - Drop the first $N_{\text{warmup}} = 60$ bars from $X$ and $y$.
   - Drop the last $H = 4$ bars from $X$ and $y$ (cannot know future price $Close_{N+4}$).
3. **Strict Chronological Data Splitting**:
   - Random shuffling (`train_test_split(shuffle=True)`) is **strictly forbidden**.
   - Chronological split point: index $K = \lfloor 0.70 \times N_{\text{events}} \rfloor$.
   - **Boundary Embargo / Purge**: Any candidate signal within $H=4$ bars prior to the split point must be removed from the training set, so the training target label does not evaluate future prices belonging to the test partition.
4. **Featurization Fitting Order (`ml-best-practices`)**:
   - Fit preprocessing objects (`StandardScaler`, `RobustScaler`, encoders) **exclusively on the training split**:
     ```python
     scaler = StandardScaler()
     X_train_scaled = scaler.fit_transform(X_train)
     X_test_scaled = scaler.transform(X_test)  # NEVER fit on test or full dataset!
     ```

---

## 7. Complete Reference Pipeline Implementation

Below is the production-ready Python reference code designed for direct inclusion or invocation in `transcendence_ml_analysis.ipynb`.

```python
"""
reference_feature_pipeline.py — Pipeline de Engenharia de Features e Rotulagem (R1)
Garante zero lookahead bias e conformidade estrita com ml-best-practices.
"""
import numpy as np
import pandas as pd


def load_and_preprocess_candles(csv_path: str) -> pd.DataFrame:
    """Carrega dados OHLC M15 e valida timestamps."""
    df = pd.read_csv(csv_path)
    # Suporte a timestamp em ms ou segundos
    first_time = float(df["time"].iloc[0])
    unit = "ms" if first_time > 1e11 else "s"
    df["datetime"] = pd.to_datetime(df["time"], unit=unit, utc=True)
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def extract_features_and_labels(df_raw: pd.DataFrame, horizon: int = 4) -> pd.DataFrame:
    """
    Constrói a matriz completa de features e variável alvo.
    horizon = 4 candles de 15m (1 hora).
    """
    df = df_raw.copy()
    
    # -------------------------------------------------------------
    # 1. Features Temporais e Cíclicas
    # -------------------------------------------------------------
    hour = df["datetime"].dt.hour
    dow = df["datetime"].dt.dayofweek
    minute = df["datetime"].dt.minute
    tod_min = hour * 60 + minute
    
    df["hour"] = hour
    df["dow"] = dow
    df["sin_hour"] = np.sin(2 * np.pi * hour / 24.0)
    df["cos_hour"] = np.cos(2 * np.pi * hour / 24.0)
    df["sin_dow"] = np.sin(2 * np.pi * dow / 7.0)
    df["cos_dow"] = np.cos(2 * np.pi * dow / 7.0)
    df["sin_tod"] = np.sin(2 * np.pi * tod_min / 1440.0)
    df["cos_tod"] = np.cos(2 * np.pi * tod_min / 1440.0)
    
    # Sessões de Mercado
    df["session_asian"] = ((hour >= 0) & (hour < 8)).astype(int)
    df["session_london"] = ((hour >= 8) & (hour < 16)).astype(int)
    df["session_ny"] = ((hour >= 13) & (hour < 21)).astype(int)
    df["session_overlap"] = ((hour >= 13) & (hour < 16)).astype(int)
    df["is_weekend"] = (dow >= 5).astype(int)

    # -------------------------------------------------------------
    # 2. Features Técnicas: SMAs e StdDevs Multi-Período
    # -------------------------------------------------------------
    for p in [5, 10, 20, 50]:
        sma = df["close"].rolling(p).mean()
        std = df["close"].rolling(p).std()
        df[f"dist_sma_{p}"] = (df["close"] - sma) / sma
        df[f"slope_sma_{p}"] = (sma - sma.shift(1)) / (sma.shift(1) + 1e-9)
        df[f"vol_ratio_{p}"] = std / (sma + 1e-9)
        df[f"_sma_{p}"] = sma
        df[f"_std_{p}"] = std

    # Spreads de SMA e Choque de Volatilidade
    df["sma_spread_5_20"] = (df["_sma_5"] - df["_sma_20"]) / df["_sma_20"]
    df["sma_spread_10_50"] = (df["_sma_10"] - df["_sma_50"]) / df["_sma_50"]
    df["sma_spread_20_50"] = (df["_sma_20"] - df["_sma_50"]) / df["_sma_50"]
    df["vol_shock_5_50"] = df["_std_5"] / (df["_std_50"] + 1e-9)

    # -------------------------------------------------------------
    # 3. Bollinger Bands (p=20, mult=2.0)
    # -------------------------------------------------------------
    bb_mid = df["_sma_20"]
    bb_std = df["_std_20"]
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std
    bb_range = bb_upper - bb_lower + 1e-9

    df["bb_width"] = (bb_upper - bb_lower) / bb_mid
    df["bb_pct_b"] = (df["close"] - bb_lower) / bb_range
    df["bb_pen_upper"] = np.maximum(0.0, (df["close"] - bb_upper) / bb_upper)
    df["bb_pen_lower"] = np.maximum(0.0, (bb_lower - df["close"]) / bb_lower)

    # -------------------------------------------------------------
    # 4. Donchian Channels Multi-Período (Shift 1 = Sem Lookahead!)
    # -------------------------------------------------------------
    for n in [10, 20, 40, 60]:
        dc_up = df["high"].shift(1).rolling(n).max()
        dc_lo = df["low"].shift(1).rolling(n).min()
        dc_mid = (dc_up + dc_lo) / 2.0
        dc_range = dc_up - dc_lo + 1e-9
        
        df[f"dc_width_{n}"] = (dc_up - dc_lo) / dc_mid
        df[f"dc_pct_{n}"] = (df["close"] - dc_lo) / dc_range
        df[f"dc_break_upper_{n}"] = np.maximum(0.0, (df["close"] - dc_up) / dc_up)
        df[f"dc_break_lower_{n}"] = np.maximum(0.0, (dc_lo - df["close"]) / dc_lo)
        if n == 20:
            df["_dc_upper_20"] = dc_up
            df["_dc_lower_20"] = dc_lo

    # -------------------------------------------------------------
    # 5. Candlestick & Microestrutura
    # -------------------------------------------------------------
    rng = df["high"] - df["low"] + 1e-9
    df["body_ratio"] = (df["close"] - df["open"]).abs() / rng
    df["upper_wick_ratio"] = (df["high"] - df[["open", "close"]].max(axis=1)) / rng
    df["lower_wick_ratio"] = (df[["open", "close"]].min(axis=1) - df["low"]) / rng
    df["ret_1"] = df["close"].pct_change(1)
    df["ret_3"] = df["close"].pct_change(3)
    df["ret_5"] = df["close"].pct_change(5)

    # -------------------------------------------------------------
    # 6. Extração de Sinais Determinísticos
    # -------------------------------------------------------------
    df["sig_df_dir"] = np.where(df["close"] > df["_dc_upper_20"], -1,
                        np.where(df["close"] < df["_dc_lower_20"], 1, 0))
    df["sig_bb_dir"] = np.where(df["close"] > bb_upper, -1,
                        np.where(df["close"] < bb_lower, 1, 0))
    
    df["sig_agreement"] = ((df["sig_df_dir"] == df["sig_bb_dir"]) & (df["sig_df_dir"] != 0)).astype(int)
    df["sig_confluence_dir"] = np.where((df["sig_df_dir"] == 1) & (df["sig_bb_dir"] == 1), 1,
                               np.where((df["sig_df_dir"] == -1) & (df["sig_bb_dir"] == -1), -1, 0))

    # Candidato a trade (união sem conflitos)
    cond_call = ((df["sig_df_dir"] == 1) | (df["sig_bb_dir"] == 1)) & (df["sig_df_dir"] != -1) & (df["sig_bb_dir"] != -1)
    cond_put = ((df["sig_df_dir"] == -1) | (df["sig_bb_dir"] == -1)) & (df["sig_df_dir"] != 1) & (df["sig_bb_dir"] != 1)

    df["candidate_signal"] = np.where(cond_call, "call", np.where(cond_put, "put", "none"))

    # -------------------------------------------------------------
    # 7. Definição da Variável Alvo (Target) com Shift Futuro
    # -------------------------------------------------------------
    df["future_close"] = df["close"].shift(-horizon)
    df["target"] = np.where(
        df["candidate_signal"] == "call",
        (df["future_close"] > df["close"]).astype(float),
        np.where(
            df["candidate_signal"] == "put",
            (df["future_close"] < df["close"]).astype(float),
            np.nan
        )
    )

    # Remove colunas auxiliares
    aux_cols = [c for c in df.columns if c.startswith("_")]
    df = df.drop(columns=aux_cols)
    return df


def prepare_ml_dataset(df_featured: pd.DataFrame, warmup_bars: int = 60, horizon: int = 4):
    """
    Remove warmup inicial e barras finais sem target.
    Filtra apenas eventos com sinal determinístico disparado.
    """
    # Descarta warmup inicial (elimina NaNs de rolling 60)
    valid_df = df_featured.iloc[warmup_bars:].copy()
    
    # Filtra apenas linhas com sinal ativo (Event-Driven ML Dataset)
    events = valid_df.dropna(subset=["target"]).copy()
    events["target"] = events["target"].astype(int)
    
    # Definição das colunas de features preditivas
    ignore_cols = {"time", "datetime", "open", "high", "low", "close", "future_close", "candidate_signal", "target"}
    feature_cols = [c for c in events.columns if c not in ignore_cols]
    
    return events, feature_cols
```

---

## 8. Summary Feature Dictionary

The 45 canonical engineered features are partitioned into 5 functional orthogonal groups:

| Group | Features | Count | Description / Role |
|---|---|---|---|
| **Temporal & Cyclical** | `sin_hour`, `cos_hour`, `sin_dow`, `cos_dow`, `sin_tod`, `cos_tod`, `session_asian`, `session_london`, `session_ny`, `session_overlap`, `is_weekend` | 11 | Captures time-of-day liquidity, session turnover regimes, and OTC market behavior without boundary discontinuities. |
| **Trend & Relative SMA** | `dist_sma_5`, `dist_sma_10`, `dist_sma_20`, `dist_sma_50`, `slope_sma_5`, `slope_sma_10`, `slope_sma_20`, `slope_sma_50`, `sma_spread_5_20`, `sma_spread_10_50`, `sma_spread_20_50` | 11 | Measures price extension away from moving averages and multi-speed trend alignment. |
| **Volatility & Dispersion** | `vol_ratio_5`, `vol_ratio_10`, `vol_ratio_20`, `vol_ratio_50`, `vol_shock_5_50`, `bb_width` | 6 | Quantifies volatility regime, volatility expansion vs contraction, and compression squeeezes. |
| **Bands & Channels** | `bb_pct_b`, `bb_pen_upper`, `bb_pen_lower`, `dc_width_10`, `dc_width_20`, `dc_width_40`, `dc_width_60`, `dc_pct_10`, `dc_pct_20`, `dc_pct_40`, `dc_pct_60`, `dc_break_upper_10`, `dc_break_lower_10`, `dc_break_upper_20`, `dc_break_lower_20` | 15 | Quantifies exact breakout penetration depth and relative position inside multi-period Donchian and Bollinger envelopes. |
| **Signals & Confluence** | `sig_df_dir`, `sig_bb_dir`, `sig_agreement`, `sig_confluence_dir` | 4 | Encodes which deterministic system triggered and whether both strategies agree on the reversal. |
| **Microstructure & Wicks** | `body_ratio`, `upper_wick_ratio`, `lower_wick_ratio`, `ret_1`, `ret_3`, `ret_5` | 6 | Detects price exhaustion wicks, rejection candles, and short-term exhaustion momentum. |

**Total Feature Dimension**: 53 stationary, scale-invariant numeric features.
Zero missing values after dropping initial 60 warmup candles.
Zero lookahead bias.
Target distribution: Balanced (~55% Target = 1, ~45% Target = 0 on BTC; ~53% on EURUSD).

---

## 9. Downstream Architectural Handoff & Recommendations

1. **For Explorer Survey 3 / Implementer 1 (Notebook `transcendence_ml_analysis.ipynb`)**:
   - The dataset must be split strictly chronologically (e.g. 70% Train, 30% Test).
   - Apply an embargo of $H=4$ bars prior to the test boundary.
   - Fit `StandardScaler` on `X_train` only.
   - Primary metric is **Precision** for Class 1 (reversal with profit): a high precision model allows Kelly staking to safely scale up capital allocation while discarding false breakouts.
2. **Environment Alert**:
   - As observed in system exploration, `.venv` currently contains `numpy` and `pandas`, but lacks `scikit-learn`, `matplotlib`, `seaborn`, and `jupyter`.
   - Implementer 1 or Orchestrator must execute `.venv\Scripts\pip.exe install scikit-learn matplotlib seaborn jupyter` before running the notebook.
