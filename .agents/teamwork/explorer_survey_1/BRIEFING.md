# BRIEFING — 2026-09-25T02:48:30Z

## Mission
Survey codebase for deterministic trading strategies (`donchian_fade`, `bollinger_touch`, etc.) and candle data / historical mock generators.

## 🔒 My Identity
- Archetype: explorer
- Roles: Codebase & Deterministic Strategies Analyst
- Working directory: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_1
- Original parent: f6bff82c-856d-4a65-b651-d80d719d28be
- Milestone: Survey Codebase and Deterministic Strategies

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Output reports to report.md and handoff.md in explorer_survey_1

## Current Parent
- Conversation ID: f6bff82c-856d-4a65-b651-d80d719d28be
- Updated: 2026-09-25T02:48:30Z

## Investigation State
- **Explored paths**: `strategies.py`, `config.py`, `bot.py`, `research/grid_families.py`, `run_donchian_fade.py`, `run_eurusd_boll_donchian.py`, `backtest_hunter_donchian_h1.py`, `backtest_bollinger_m15.py`, `data/*.csv`, `build_eurusd_histdata.py`, `fetch_binance.py`, `fetch_vision.py`, `fetch_iq.py`, `sandbox_test_multi_mean.py`, `tests/test_homeostasis.py`, `synaptic_hypervisor/sidecar/daemon.py`, `.venv/Scripts/python.exe`.
- **Key findings**:
  - `donchian_fade_signal` and `bollinger_touch_signal` located and fully mapped in `strategies.py`.
  - 18 CSV price history files cataloged; primary dataset is `data/EURUSD_M15_histdata.csv` (40,000 candles).
  - Raw 1-hour win rates on EURUSD are 52.75% (Donchian) and 53.11% (Bollinger), falling short of broker breakeven (53.48% - 55.56%), proving the need for an ML classification filter.
  - Python 3.12.0 virtualenv active at `.venv\Scripts\python.exe`; ML libraries (`scikit-learn`, `xgboost`, `matplotlib`, `seaborn`, `nbconvert`) need installation by Implementer 1.
  - Findings fully synthesized with Explorers 2 & 3.
- **Unexplored areas**: None within the survey scope.

## Key Decisions Made
- Selected `data/EURUSD_M15_histdata.csv` as the primary asset for R1/R2 training due to matching the bot's default OTC forex asset (`EURUSD-OTC`).
- Formulated zero-lookahead vectorization rule (`high.shift(1).rolling(n).max()`).
- Established mathematical proof of edge gap vs broker payout.

## Artifact Index
- `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_1\report.md` — Full technical survey report
- `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_1\handoff.md` — 5-component handoff report
- `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_1\progress.md` — Liveness heartbeat
