# Orchestration Plan: Projeto Híbrido de Transcendência

## Objective
Implement and rigorously evaluate a Machine Learning Classification filter over deterministic signals (`donchian_fade`, `bollinger_touch`) to predict signal quality and filter false breakouts, documented in an executable Jupyter Notebook (`transcendence_ml_analysis.ipynb`) adhering strictly to `ml-best-practices` and verified by multi-agent review and forensic audit.

## Phases & Milestones

### Phase 0: Survey & Scope Mapping
- Spawn 3 parallel Explorers to investigate:
  1. Explorer 1: Codebase inventory, location of `donchian_fade` and `bollinger_touch`, existing candle/price data sources or historical mock structures.
  2. Explorer 2: Feature engineering specifications, technical indicators (SMA, StdDev multi-period), temporal features, target labeling logic (Target = 1 if reversed with profit in next hour).
  3. Explorer 3: ML modeling requirements, chronological splitting (TimeSeriesSplit) to prevent lookahead bias, model baselines (Logistic Regression vs Random Forest/XGBoost), precision-first metrics, and notebook execution requirements.
- Merge findings into `PROJECT.md` (Architecture, Feature Inventory, Interface Contracts, Code Layout).

### Phase 1: Implementation (Iteration Loop)
- Worker:
  - Implement data loading and feature extraction pipeline (temporal features, SMA, StdDev, `donchian_fade`, `bollinger_touch` signals, Target variable).
  - Create `transcendence_ml_analysis.ipynb` with EDA, strict chronological split before scaling, Base and Advanced models.
  - Add explanatory Markdown cells after every evaluation cell per `ml-best-practices`.
  - Conclude with final Markdown table comparing Precision, Recall, and F1-Score (prioritizing Precision).
  - Execute notebook end-to-end to verify zero syntax/import/runtime errors.

### Phase 2: Independent Review & Challenger Verification
- 2 Reviewers: Verify code quality, absence of lookahead bias, strict chronological splitting, execution integrity, adherence to `ml-best-practices`.
- 2 Challengers: Verify empirical correctness, test edge cases (temporal order, metric computations, class imbalance, precision ranking).

### Phase 3: Forensic Integrity Audit & Gate
- Forensic Auditor (`teamwork_preview_auditor`): Check for hardcoding, dummy logic, lookahead leakage, data fabrication, or metric falsification.
- Gate Evaluation: Strict AND across Reviewers, Challengers, and Auditor.

### Phase 4: Final Synthesis & Completion Reporting
- Record retrospective in `progress.md`, write `handoff.md`, report completion to parent agent.
