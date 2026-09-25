# Dispatch Instructions

## 2026-09-25T02:38:23Z

Source: Parent Agent (id: d9b29ae3-193c-4d0d-9060-8f10788fa480)

You are the Project Orchestrator for the Projeto Híbrido de Transcendência.

Working Directory: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\orchestrator_1
Project Root: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta
Original User Request: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\ORIGINAL_REQUEST.md (Read the latest entry ## 2026-09-25T02:37:35Z)

Your Mission:
Decompose, dispatch, coordinate, and synthesize the work required to implement the ML Classification filter over deterministic signals (`donchian_fade`, `bollinger_touch`).

Key Requirements from User Request:
1. R1. Pipeline de Engenharia de Dados e Features:
   Load price history (.csv or mock historical data if needed) and extract temporal features, technical features (SMA, StdDev of multiple periods), and signal indication from strategies `donchian_fade` and `bollinger_touch`. Create target variable (Target = 1 if price reversed with profit in next hour, 0 if false breakout).
2. R2. Modelagem Híbrida e Comparação:
   Create structured Jupyter Notebook (`transcendence_ml_analysis.ipynb`) containing Exploratory Data Analysis (EDA). Train and compare at least one Base model (e.g. Logistic Regression) and one Advanced model (e.g. Random Forest/XGBoost). Order of featurization must be strict: split train/test chronologically BEFORE fitting scalers/encoders to avoid lookahead bias.
3. R3. Análise em Markdown (ML Best Practices):
   Every evaluation code block in the Notebook must be followed by a Markdown cell explaining the mathematical results and model behavior, strictly following `ml-best-practices` (see `C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\ml_best_practices\SKILL.md`). Also refer to `notebook-guidance` (`C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\notebook_guidance\SKILL.md`).
4. Acceptance Criteria:
   - Notebook runs end-to-end without syntax or library import errors (verifiable executing all cells via python engine).
   - Validation split is strictly chronological (TimeSeriesSplit) and not random.
   - Final cell presents a Markdown table listing Precision, Recall, and F1-Score of all evaluated models.
   - Mathematical evaluation must prioritize Precision (minimizing False Positives) over global Accuracy.

Keep your plan.md, progress.md, and context.md up to date in your working directory.
When complete, write your handoff.md and send a message reporting completion so independent Victory Audit can be executed.
