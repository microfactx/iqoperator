# Skill Dump: notebook-guidance
Source: C:\Users\WDAGUtilityAccount\.gemini\config\plugins\data-agent-kit-plugin\skills\notebook_guidance\SKILL.md

Core Methodology:
- Clean Final State: The final notebook MUST NOT have failed cells. 100% pass without errors.
- Logical Chunk Fidelity: Keep cells small, one logical transformation/visualization per cell. Group related cells logically.
- Final Summary Cell: Markdown cell (no code, no starting with code block) grounded strictly in numerical data.
- Structured Conclusion: MUST strictly contain exactly these three sections:
  ### Q&A
  ### Data Analysis Key Findings
  ### Insights or Next Steps
- Plotting: Readable colors, adjusted figure sizes, no overlapping legends/labels, inline plots.
