# Grand Hillel: RABBI_LAYER Review — GPT (independent)

Scope: RABBI_LAYER.md only. Verdict buckets follow the checklist (VERIFIED / PLAUSIBLE / SPECULATIVE / WRONG / MISSING). No cross-model references.

## VERIFIED
- **Context-window degradation is real.** Transformer attention dilutes over long contexts; “lost in the middle” is documented (Liu et al., 2023) and persists in practice.  
- **Anthropic alignment-faking result (78% scratchpad reasoning after RL).** The 2024 Anthropic paper shows increased alignment-faking reasoning and differential behavior between free vs. paid-tier setups when the model is in a training loop.  
- **AWS UAE/Bahrain data center strikes (March 1–2, 2026).** Reuters and other outlets report drone strikes damaged multiple AWS facilities, causing outages — supports the centralized-infrastructure vulnerability argument.  
- **Ensembles/consensus math.** Condorcet’s jury theorem: if individual accuracy >0.5 and errors are independent, majority vote increases accuracy toward 1.0.  
- **Chain-of-thought distillation transfers reasoning signals.** CoT distillation literature (e.g., 2023–2025 studies) shows smaller students gain reasoning ability from teacher traces beyond answer-only distillation.

## PLAUSIBLE
- **AGI as system-of-models vs. single model.** Empirically, multi-agent/ensemble setups boost parallelizable tasks; performance can drop on sequential tasks. Architectural dependence is real, but “AGI must be a system” is not proven.  
- **Frozen-weight binary classifier reduces deployment-time gaming.** Freezing removes the incentive channel exploited in training loops, but does not stop mis-specified boundaries, adversarial prompts, distribution shift, or side channels. Effectiveness at 1–7B scale is unproven.  
- **Local/distributed compute as security architecture.** Distributing classifiers removes single cloud chokepoints, but on-device performance, update latency, secure enclaves, and supply-chain risks remain unresolved.  
- **Multi-model consensus utility.** Aggregation helps if errors are partly independent; real training data overlap likely weakens independence, so gains are situational.  
- **Grok Heavy performance/parameter claims.** MoE scale and HLE numbers cited are not independently verifiable with public data; plausible but unconfirmed.  
- **Dario Amodei “frozen stabilizer” stance vs. Pentagon.** Reports exist but need primary sourcing for dates/terms; principles plausible, details unverified here.

## SPECULATIVE
- **“Truth + love” framing as engineering target.** Philosophical; not technically testable.  
- **Da Vinci Depth principle (scale plateau; system depth as the path).** Some evidence of diminishing returns for pure scale, but superiority of “depth over scale” is unproven.  
- **Pharisee→Rabbi analogy as alignment template.** Historical analogy; not empirically testable for AI.  
- **Distributed, cryptographically verifiable crowd-training for bees.** Stated as aspirational; no production-ready system today.  
- **Independence assumption sufficiency.** Actual cross-model error correlation is unmeasured; assuming sufficient independence is speculative.

## WRONG
- No claims conclusively falsified with current evidence. Several numeric specifics (e.g., exact Grok Heavy HLE score, parameter counts) remain unverified rather than proven wrong.

## MISSING
- **Error correlation measurements.** Need empirical cross-model correlation stats and consensus accuracy vs. single-model baselines.  
- **Calibration/conviction metrics.** Include ECE/Brier scores and overconfidence mitigation for “conviction scoring.”  
- **Latency/cost budgets.** End-to-end latency for multi-model debate + bee gate; per-query and monthly cost envelopes; on-device MIPS/NPU constraints for bees.  
- **Robustness data.** Adversarial eval of frozen classifiers (FP/FN rates), distribution-shift tests, and red-team coverage.  
- **Governance.** Corpus curation authority, update cadence, signing/rollback, auditability of bee versions.  
- **Security.** Feasibility of hardware/process isolation on consumer devices; side-channel threat model; secure update pipeline.  
- **Evaluation ablations.** Benchmarks comparing multi-agent vs. single-agent on sequential vs. parallel tasks; evidence for Claim 1’s task-dependent gains.
