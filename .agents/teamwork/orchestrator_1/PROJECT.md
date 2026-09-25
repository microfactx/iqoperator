# Project: Projeto Híbrido de Transcendência

## Architecture
- **Objective**: Implement a Machine Learning Classification filter over deterministic signals (`donchian_fade` and `bollinger_touch`) to predict signal quality and filter false breakouts.
- **Artifact**: `transcendence_ml_analysis.ipynb` in the project root (`c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\transcendence_ml_analysis.ipynb`).
- **Runtime Environment**: Python 3.12 virtual environment at `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.venv\Scripts\python.exe`.
- **Dataset**: Primary dataset `data/EURUSD_M15_histdata.csv` (40,000 M15 candles) with cross-validation on `data/BTCUSDT_M15_1y.csv` (35,000 M15 candles).
- **Featurization Flow**:
  1. Candle Loading & Chronological Sorting.
  2. Scale-Invariant Feature Engineering (Temporal cyclical encodings, multi-period SMAs, rolling StdDevs, Bollinger Bands, Donchian Channels, Candlestick morphology, Signal indicators).
  3. Zero-Lookahead Target Formulation ($H=4$ candles for M15, 1-hour reversal profit).
  4. Chronological Train/Test Split (80/20, `shuffle=False`) **strictly prior** to fitting scalers/encoders.
  5. Cross-Validation: `TimeSeriesSplit(n_splits=5)`.
  6. Modeling: Base Model (Logistic Regression) vs Advanced Models (Random Forest & XGBoost).
  7. Precision-First Calibration (minimizing False Positives to achieve $>60\%$ win rate).
  8. Detailed Storytelling Markdown cells paired with every evaluation code cell adhering to `ml-best-practices`.
  9. Final Comparison Markdown Table and 3-Section Conclusion (`### Q&A`, `### Data Analysis Key Findings`, `### Insights or Next Steps`) adhering to `notebook-guidance`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | `env_dependencies` | Install `scikit-learn`, `xgboost`, `matplotlib`, `seaborn`, `ipykernel`, `nbconvert` in `.venv` | M1 | Survey |
| 2 | `data_ingestion` | Load and validate `data/EURUSD_M15_histdata.csv` without gaps or unhandled nulls | M1 | Survey / R1 |
| 3 | `temporal_features` | 11 cyclical features: $\sin/\cos$ for hour, day of week, minute, and session flags | M1 | Survey / R1 |
| 4 | `technical_features` | Multi-period SMA (5, 10, 20, 50) distances/slopes, rolling StdDev (5, 10, 20, 50) shock ratios | M1 | Survey / R1 |
| 5 | `band_channel_features` | Bollinger Bands (%B, bandwidth) and multi-period Donchian Channels (10, 20, 40, 60) | M1 | Survey / R1 |
| 6 | `signal_extraction` | Vectorized `donchian_fade` ($n=20$) and `bollinger_touch` ($p=20, 2\sigma$) signals with agreement flags | M1 | Survey / R1 |
| 7 | `target_labeling` | Target = 1 if price reversed with profit in next hour ($H=4$ bars), 0 if false breakout; warmup/tail purging | M1 | Survey / R1 |
| 8 | `eda_visualizations` | Visualizations of distributions, correlations, class balance, and volatility patterns | M1 | Survey / R2 |
| 9 | `chronological_split` | Strict chronological 80/20 train/test split BEFORE fitting scalers to avoid lookahead bias | M1 | Survey / R2 |
| 10 | `base_model_lr` | Logistic Regression baseline with StandardScaler in Pipeline evaluated via TimeSeriesSplit CV | M1 | Survey / R2 |
| 11 | `advanced_model_rf` | Random Forest Classifier evaluated via TimeSeriesSplit CV | M1 | Survey / R2 |
| 12 | `advanced_model_xgb` | XGBoost Classifier evaluated via TimeSeriesSplit CV | M1 | Survey / R2 |
| 13 | `precision_optimization` | Decision threshold tuning prioritizing Precision (minimizing False Positives) over Accuracy | M1 | Survey / R2 |
| 14 | `markdown_storytelling` | Explanatory Markdown cells following every evaluation code block per `ml-best-practices` | M1 | Survey / R3 |
| 15 | `final_summary_table` | Final Markdown cell with summary table (Precision, Recall, F1-Score) and 3-section conclusion per `notebook-guidance` | M1 | Survey / R3 |
| 16 | `end_to_end_execution` | Full headless execution of `transcendence_ml_analysis.ipynb` verifying zero runtime errors | M1 | Survey / Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | `ml_notebook_implementation` | Implement data engineering pipeline, EDA, chronological split, models, and markdown storytelling in `transcendence_ml_analysis.ipynb` | none | IN_PROGRESS |
| 2 | `e2e_verification_and_audit` | Multi-agent review (2 Reviewers), empirical stress testing (2 Challengers), and forensic integrity audit (1 Auditor) | M1 | PLANNED |

## Interface Contracts
### Data Ingestion & Engineering $\leftrightarrow$ Notebook Pipeline
- Input: `data/EURUSD_M15_histdata.csv` (schema: `time,open,high,low,close`)
- Output Matrix: $X \in \mathbb{R}^{N \times 53}$, $y \in \{0, 1\}^N$
- Invariant: Zero forward leakage; $High_{t}$ and $Low_{t}$ excluded from Donchian boundaries using `shift(1)`.
- Warmup: First 60 rows dropped. Tail: Final 4 rows purged.

### Model Pipeline $\leftrightarrow$ Evaluation
- Scaler: `StandardScaler` fitted strictly on $X_{\text{train}}$.
- Split: Chronological 80% train ($N \approx 4,880$), 20% test ($N \approx 1,220$).
- CV: `TimeSeriesSplit(n_splits=5)` on training partition.
- Output Metrics: Precision, Recall, F1-Score, PR-AUC, Accuracy, Confusion Matrix.
- Priority: Precision is prioritized over global Accuracy.

## Code Layout
- Notebook: `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\transcendence_ml_analysis.ipynb`
- Primary Data: `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\data\EURUSD_M15_histdata.csv`
- Secondary Data: `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\data\BTCUSDT_M15_1y.csv`
- Existing Strategies: `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\strategies.py`
- Agent Workspaces: `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\`
