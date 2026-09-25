# Skill Dump: ml-best-practices
Source: C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\ml_best_practices\SKILL.md

Core Methodology:
- Data Storytelling: Ensure every code cell is followed by a markdown cell analyzing mathematical results and model behavior.
- Classification & Comparisons: Establish naive and simple ML baselines (Logistic Regression) vs Advanced (Random Forest, XGBoost).
- Strict Featurization Ordering: Always split data chronologically into train and test BEFORE fitting scalers or preprocessing pipelines. Fit scalers on train only.
- Evaluation: Metrics beyond accuracy (Precision, Recall, F1, PR-AUC). For binary trading, prioritize Precision (minimizing False Positives).
- Confusion Matrices and slice/error analysis.
