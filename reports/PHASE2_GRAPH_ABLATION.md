# RiskOrbit — Phase 2 Graph Feature Ablation Report

Controlled experiment: same held-out test set, same evaluation methodology.
Threshold selected on validation partition for each model.

| Model | Description | N Features | Threshold | Precision | Recall | F1 | PR-AUC | FPR | FP Cost | Pat A Recall | Pat B Recall | Pat C Recall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Phase 1 Frozen Baseline | 36 | 0.35 | 0.3517 | 0.2862 | 0.3156 | 0.0969 | 0.0054 | ₹19,890 | 0.0069 | 0.0455 | 0.7843 |
| **B** | Phase 1 + Simple Graph Aggregates | 39 | 0.46 | 0.5355 | 0.2862 | 0.3730 | 0.1530 | 0.0025 | ₹9,360 | 0.0000 | 0.0000 | 0.8137 |
| **C** | Phase 1 + Full Graph Features | 46 | 0.46 | 0.5425 | 0.2862 | 0.3747 | 0.1529 | 0.0025 | ₹9,100 | 0.0000 | 0.0000 | 0.8137 |
| **D** | Phase 1 + ring_risk_score Only | 37 | 0.44 | 0.4301 | 0.2862 | 0.3437 | 0.1221 | 0.0039 | ₹14,300 | 0.0000 | 0.0000 | 0.8137 |
| **E** | Phase 2 Full (riskorbit-risk-v2) | 46 | 0.32 | 0.3812 | 0.2379 | 0.2930 | 0.1140 | 0.0040 | ₹14,560 | 0.0000 | 0.0227 | 0.6667 |

## Analysis

### Graph vs Agent Value
Models A–E isolate the contribution of each component:
- **Model B–D vs A**: Graph feature value over Phase 1 baseline.
- **Model E vs C**: Effect of end-to-end retraining with graph features vs ad-hoc column addition.
- The LLM/Evidence Agent adds case interpretability but does NOT change the detection model.

### Scientific Honesty
> Any metric improvement in Phase 2 should be attributed to the graph feature engineering,
> not to the LLM evidence agent. The evidence agent serves case presentation, not detection.