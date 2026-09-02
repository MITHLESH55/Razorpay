# RiskOrbit — Hard-Negative Graph Evaluation Report (Phase 2)

**Evaluation of Legitimate Confuser Categories through Relationship Intelligence Layer**

---

| Confuser Category | Support (Txns) | Phase 1 FP | Phase 1 FPR | Phase 2 FP | Phase 2 FPR | Safety Assessment |
|---|---|---|---|---|---|---|
| **Household Sharing** | 905 | 0 | 0.00% | 0 | 0.00% | SAFE (Hubness & low refund rate guard) |
| **Shared Network (Office/Campus)** | 1,192 | 0 | 0.00% | 0 | 0.00% | SAFE (Aggressive IP hubness discount) |
| **High Refund Customer (Serial Returner)** | 1,117 | 0 | 0.00% | 0 | 0.00% | SAFE (Single account isolation guard) |
| **Multi-Device Customer** | 601 | 0 | 0.00% | 0 | 0.00% | SAFE (No multi-account linking) |
| **High-Volume Merchant Shopper** | 9,558 | 0 | 0.00% | 0 | 0.00% | SAFE (Merchant hubness exclusion) |
| **General Legitimate Population** | 14,928 | 153 | 1.02% | 112 | 0.75% | IMPROVED (-41 false positives) |

## Summary
The graph relationship layer did NOT introduce false alarms on legitimate shared infrastructure. Overall false-positive count decreased from 153 to 112, reducing modeled friction cost from ₹19,890 to ₹14,560.