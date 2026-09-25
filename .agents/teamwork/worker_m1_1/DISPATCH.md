# Dispatch: Worker M1 1 (ML Implementation Specialist)

## Mission
Implement the full data engineering, feature pipeline, and machine learning classification analysis in `transcendence_ml_analysis.ipynb` according to user requirements R1, R2, R3 and Explorer survey specifications.

## Authoritative Inputs
- `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read, especially `## 2026-09-25T02:37:35Z`)
- Project Scope: `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\orchestrator_1\PROJECT.md`
- Survey Reports:
  - `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_1\report.md` (Codebase & Strategies)
  - `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_2\report.md` (53 Features, formulas, zero-lookahead target logic)
  - `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_3\report.md` (25-cell notebook architecture, environment setup, model specs)
- Skills to Follow:
  - `C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\ml_best_practices\SKILL.md`
  - `C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\notebook_guidance\SKILL.md`

## Exclusive Write Ownership
You exclusively own:
- Package installation in `.venv`
- `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\transcendence_ml_analysis.ipynb`
- Metadata files in your working directory `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\worker_m1_1\`

## Requirements & Constraints
1. **Environment Setup**:
   Install missing dependencies into `.venv`:
   `& "c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.venv\Scripts\python.exe" -m pip install scikit-learn xgboost matplotlib seaborn ipykernel nbconvert`
2. **Notebook Implementation (`transcendence_ml_analysis.ipynb`)**:
   Implement the 25-cell notebook structure specified in Explorer 3's report:
   - Data Ingestion & Preprocessing: Load `data/EURUSD_M15_histdata.csv` (40,000 candles).
   - 53 Scale-Invariant Features: Temporal cyclical encodings ($\sin/\cos$ for hour, day of week, minute), multi-period SMAs (5, 10, 20, 50), rolling StdDevs (5, 10, 20, 50), Bollinger Bands (%B, bandwidth), Donchian Channels (10, 20, 40, 60), Candlestick morphology, and signal indicators (`donchian_fade` and `bollinger_touch`).
   - Zero-Lookahead Target Formulation: Target = 1 if price reversed with profit in next hour ($H=4$ candles in M15), 0 if false breakout; warmup (60 bars) and tail (4 bars) dropped; filter to candidate signal events.
   - Exploratory Data Analysis (EDA) visualizations: distributions, correlations, class balance, volatility.
   - Strict Featurization Ordering & Chronological Split: 80% train, 20% holdout test with `shuffle=False` strictly BEFORE fitting scalers/encoders.
   - Cross-Validation: `TimeSeriesSplit(n_splits=5)` on training partition.
   - Models: Base Model (Logistic Regression) vs Advanced Models (Random Forest & XGBoost) inside `Pipeline(StandardScaler, Model)`.
   - Precision-First Threshold Calibration: sweep threshold to minimize False Positives and demonstrate elevation of win rate above 60%.
   - Markdown Storytelling: Every evaluation code block must be followed by a comprehensive Markdown cell explaining mathematical results and model behavior per `ml-best-practices`.
   - Final Markdown Summary: Present comparison table listing Precision, Recall, and F1-Score of all evaluated models (prioritizing Precision over global Accuracy), followed strictly by the three required sections:
     - `### Q&A`
     - `### Data Analysis Key Findings`
     - `### Insights or Next Steps`
3. **Execution Verification**:
   Execute the notebook end-to-end using:
   `& "c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.venv\Scripts\python.exe" -m jupyter nbconvert --to notebook --execute transcendence_ml_analysis.ipynb --output transcendence_ml_analysis.ipynb`
   Ensure exit code is 0 and all cell outputs are populated.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverables
- Working Directory: `c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\worker_m1_1`
- Comprehensive report: `report.md`
- 5-Component handoff: `handoff.md`
- Send completion message to parent orchestrator.

## 2026-09-25T02:49:35Z
You are Worker M1 1 (ML Implementation Specialist).
Working Directory: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\worker_m1_1
Dispatch Instructions: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\worker_m1_1\DISPATCH.md
Authoritative User Request: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\ORIGINAL_REQUEST.md (MUST read, especially ## 2026-09-25T02:37:35Z).
Project Specification: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\orchestrator_1\PROJECT.md
Skills to strictly follow:
- C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\ml_best_practices\SKILL.md
- C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\notebook_guidance\SKILL.md
Survey Reports to incorporate:
- c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_1\report.md
- c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_2\report.md
- c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\explorer_survey_3\report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Install required packages in .venv: scikit-learn, xgboost, matplotlib, seaborn, ipykernel, nbconvert.
2. Implement the 25-cell transcendence_ml_analysis.ipynb according to R1, R2, R3, explorer survey blueprints, and ml-best-practices.
   - Strict chronological train/test split (80/20, shuffle=False) BEFORE fitting any scalers.
   - TimeSeriesSplit(n_splits=5) cross validation.
   - Base model (Logistic Regression) vs Advanced models (Random Forest, XGBoost).
   - Explanatory Markdown cells following every evaluation code block analyzing mathematical results.
   - Precision-first optimization (minimizing False Positives).
   - Final cell Markdown table comparing Precision, Recall, and F1-Score of all evaluated models, followed strictly by ### Q&A, ### Data Analysis Key Findings, and ### Insights or Next Steps.
3. Headless execution verification:
   Execute transcendence_ml_analysis.ipynb end-to-end via .venv python engine using jupyter nbconvert and ensure 100% pass without errors.
4. Document all steps, commands, and outputs in report.md and handoff.md in your working directory.
5. Send completion message to parent orchestrator.
