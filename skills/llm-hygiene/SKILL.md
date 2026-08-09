---
id: llm-hygiene
family: hygiene
version: 0.0.1
objective: >
  Verify LLM behavior: prompt sensitivity, output consistency,
  hallucination rate, context retention, and tool-use reliability.
inputs:
  - project_root
  - model_config
actions:
  - test prompt sensitivity
  - measure consistency
  - detect hallucinations
  - test context retention
experiments:
  - prompt_sensitivity
  - output_consistency
  - hallucination_detection
  - context_retention
  - tool_use_reliability
evidence_required:
  - llm_results.json
  - consistency_report.json
  - hallucination_log.json
success_conditions:
  - outputs stable for same prompt
  - no hallucinations on known facts
  - tool calls reliable
failure_conditions:
  - prompt-sensitive outputs
  - hallucination detected
  - tool call failure
artifacts:
  - llm_results.json
  - consistency_report.json
---

# LLM Hygiene

## PURPOSE
Verify LLM behavior and reliability.
