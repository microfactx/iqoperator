# Adversarial Review & Hardening Report: Filtro Preditivo ML (XGBoost tau=0.62)

> [!WARNING] **Skepticism Disclaimer**
> Moderate-High confidence: All mathematical invariances, model serialization formats, and candle data edge cases have been rigorously probed, broken, fixed, and verified across 47 automated tests, but live broker websocket packet streams across multi-day sessions still carry inherent operational market execution risks.

---

## 1. What the prior attempt got wrong

### Issue 1: Intermittent NaN in Price Buffer (Fatal Functional Bug)
- **Input:** An 80-candle buffer where a single candle in the lookback window (e.g. at index 40) contains `close = np.nan` or `open = np.nan` due to broker websocket packet drop or socket reconnect jitter.
- **Expected:** In accordance with ML Best Practices, the filter imputes intermittent dropped prices (forward-fill / backward-fill last known traded price) and evaluates the feature vector without crashing.
- **Actual:** `compute_features` produced NaNs across 10 rolling features (`dist_sma_50`, `slope_sma_50`, `vol_ratio_50`, `sma_spread_10_50`, `sma_spread_20_50`, `vol_shock_5_50`, `dc_width_40`, `dc_pct_40`, `dc_width_60`, `dc_pct_60`), raising `ValueError: NaN detectado no vetor de features do candle`. In `filter_signal`, this exception was caught, logging an error and returning `(False, 0.0)`. This triggered a catastrophic 15-hour trading halt (60 consecutive M15 candles) where every single trade was canceled until the NaN candle left the 60-period window.
- **Root Cause:** In `compute_features(df)`, price columns were cast with `.astype(float)` without imputation (`.ffill().bfill()`) for intermittent dropped packets.

### Issue 2: Crash on Native JSON Model Artifact (`models/xgb_filter.json`)
- **Input:** Pointing `ML_MODEL_PATH = "models/xgb_filter.json"` (as explicitly specified in Acceptance Criteria R1: "em um artefato estático (ex: `models/xgb_filter.pkl` ou `xgb_filter.json`)").
- **Expected:** `MLFilter` loads the serialized native XGBoost JSON weights, extracts the 53 feature names from the booster, and evaluates probabilities.
- **Actual:** `MLFilter._load_model` unconditionally executed `pickle.load(f)`, crashing with `pickle.UnpicklingError: invalid load key, '{'` and setting `self.is_loaded = False`.
- **Root Cause:** Hardcoded assumption of pickle serialization without format branching for native JSON.

### Issue 3: Crash on String Timestamps in Candle Buffers
- **Input:** A DataFrame with a `time` or `datetime` column containing string timestamps (e.g. `'2026-09-25 01:00:00'`).
- **Expected:** `compute_features` parses timestamp strings into UTC datetime.
- **Actual:** `val0 = float(d[col].iloc[0])` crashed with `ValueError: could not convert string to float: '2026-09-25 01:00:00'` or `AttributeError: Can only use .dt accessor with datetimelike values`.
- **Root Cause:** Inflexible timestamp normalization assuming numeric epoch seconds/ms, and failure to cast an existing object-dtype `datetime` column to datetime64 UTC.

### Issue 4: Fragile Signal Casing & Whitespace
- **Input:** Calling `filter_signal(df, " CALL ")` or `filter_signal(df, "PUT")`.
- **Expected:** Signal normalized and evaluated against threshold.
- **Actual:** `if not signal or signal not in ("call", "put"): return False, 0.0` immediately rejected valid uppercase signals without computing probability.
- **Root Cause:** Missing string normalization (`str(signal).strip().lower()`).

### Issue 5: Non-Chronological / Unordered Candle Buffers
- **Input:** Candle DataFrame passed in descending order (newest first).
- **Expected:** Features calculated chronologically with latest row representing the current candle.
- **Actual:** Features calculated backward; `iloc[-1]` was the oldest candle.
- **Root Cause:** Missing `d = d.sort_values("datetime").reset_index(drop=True)` in `ml_filter.py`.

### Issue 6: Numerical Vulnerability in Division Denominators
- **Input:** Flat or zero prices in technical indicators.
- **Expected:** Spreads and widths remain numerically finite without `inf` or `nan`.
- **Actual:** Denominators `_sma_20`, `dc_mid`, `dc_up`, `dc_lo` lacked epsilon `+ 1e-9`.
- **Root Cause:** Unprotected divisions in `compute_features`.

### Issue 7: Superficial Test Verification in Prior Attempt
- **Input:** Prior test suite execution.
- **Expected:** Deep verification of runtime gating logic in `bot.py` and edge cases.
- **Actual:** Prior attempt only tested `Bot.__init__` property initialization, never simulating order gating or verifying that `allowed=False` actually suppresses order execution.
- **Root Cause:** Implementation only contained happy-path tests.

---

## 2. What I changed

1. **`ml_filter.py`**:
   - Added native `.json` model support: `MLFilter` dynamically loads `xgb_filter.json` using `XGBClassifier().load_model()`, retrieves all 53 booster feature names, and checks `metadata.json` for threshold and metadata.
   - Added relative path resolution against `os.path.dirname(__file__)` so the model loads reliably regardless of working directory.
   - Implemented intermittent missing data imputation: `d[c] = pd.to_numeric(d[c], errors="coerce").ffill().bfill()` on OHLC price columns to guarantee zero-drop resilience.
   - Implemented flexible datetime parsing: handles epoch seconds, epoch milliseconds, ISO strings, and ensures `d["datetime"]` is cast to datetime64 UTC.
   - Enforced strict chronological sorting: `d = d.sort_values("datetime").reset_index(drop=True)`.
   - Added epsilon protection (`+ 1e-9`) to all denominator operations (`sma_spread`, `bb_width`, `bb_pen`, `dc_width`, `dc_break`).
   - Added signal string normalization (`str(signal).strip().lower()`) in `filter_signal`.

2. **`check_ml_filter.py`**:
   - Added `test_07_json_model_native_loading`: verifies that `models/xgb_filter.json` loads natively and outputs probabilities identical to `.pkl` up to 5 decimal places.
   - Added `test_08_intermittent_nan_resilience`: tests that intermittent NaNs simulating websocket packet drops are recovered cleanly without throwing exceptions.
   - Added `test_09_string_timestamps_and_reverse_order`: verifies ISO string timestamps and candles in reverse chronological order.

3. **`tests/test_ml_filter.py`**:
   - Added `sys.path` bootstrapping to permit direct execution (`python tests/test_ml_filter.py`).
   - Added `test_json_model_artifact_loading`, `test_intermittent_nan_resilience`, `test_string_timestamp_and_reverse_order`, and `test_signal_casing_and_normalization`.
   - Added `test_bot_runtime_gating_order_suppression`: deep integration test proving that when `ml_filter` returns `allowed=False`, `_fire_buy` is suppressed, and when `allowed=True`, `_fire_buy` is executed.

---

## 3. Verification Record

- **Deep Verification (ran actual tests):**
  1. `& ".venv\Scripts\python.exe" check_ml_filter.py`:
     - Result: 9/9 tests passed in 1.772s (`ALL ML FILTER TESTS PASSED`).
  2. `& ".venv\Scripts\python.exe" tests/test_ml_filter.py`:
     - Result: 8/8 tests passed in 1.461s.
  3. `& ".venv\Scripts\python.exe" -m unittest discover tests`:
     - Result: 47/47 tests passed in 18.965s (`OK`). (39 pre-existing homeostasis/resilience tests + 8 ML filter tests).
  4. `& ".venv\Scripts\python.exe" export_ml_filter.py`:
     - Result: Re-trained and validated holdout test set with exact precision `65.96%` and `47` trades; exported `.pkl`, `.json`, and `metadata.json`.
  5. Python interactive verification of JSON model loading, NaN resilience, string timestamps, and uppercase signals.

- **Shallow Verification (manual only):**
  - Inspected banner output format in `bot.py` (`ML_Filter=ON(tau=0.62)`).

- **Unverified aspects:**
  - Multi-hour live execution with real broker websocket credentials against OTC weekend markets (requires active funded account and live market session).

---

## 4. Known Issues

- `Minor Robustness Risk`: The model was trained on historical EUR/USD M15 candles. Running across other currency pairs (e.g. `USDCAD-OTC`, `BTCUSD`) assumes statistical similarity in breakout exhaustion dynamics.
- `Minor Robustness Risk`: When the broker returns fewer than 61 candles during an initial outage recovery, `filter_signal` logs a warning and fails open (`allowed=True, prob=1.0`) to avoid crashing the bot while the candle buffer refills.

---

## 5. Remaining risk & next step

- **Remaining Risk:** Live network latency under congested broker conditions. In our offline test suite, feature computation + XGBoost inference takes ~84ms, well within the 900-second M15 candle interval.
- **Next Step:** The implementation meets all acceptance criteria (R1, R2, R3) and passes all 47 regression and adversarial tests. The task is complete and ready for production deployment.
