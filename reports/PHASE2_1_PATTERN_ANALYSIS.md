# PHASE 2.1 PATTERN ANALYSIS

## Pattern Taxonomy (24 rings, 3 patterns)

### Pattern A - Coordinated Device Abuse (12 rings)

- Multiple accounts sharing >= 2 device fingerprints
- Low individual transaction signal; coordinated multi-account refund abuse
- **Detection:** Graph stream exclusively (Phase 1 score typically < threshold)
- **E2E Recall: 91.67%** (up from 0.69% Phase 1)
- Mechanism: device-sharing edges with edge_strength > 0.05, bounded 2-hop traversal

### Pattern B - IP-Sharing Network (4 rings)

- Multiple accounts sharing IP subnet or cluster
- Moderate device diversity (harder to detect than Pattern A)
- **Detection:** Graph stream primarily; Phase 1 supplemental
- **E2E Recall: 100.00%** (up from 4.55% Phase 1)
- IP edges penalized more heavily than device edges (NAT/ISP sharing risk)

### Pattern C - Refund Burst Abuse (8 rings)

- High individual refund rate; strong transaction-level signals
- Weak graph density (coordinated by timing, not shared devices)
- **Detection:** Phase 1 exclusively (graph stream gives 0% Pattern C coverage)
- **E2E Recall: 0.00%** (from 78.43% Phase 1)
- Investigation agent may expand ring membership via 2-hop traversal from Phase 1 seeds

## Cross-Pattern Summary

| Pattern | Primary Stream | Graph Coverage | P1 Coverage | E2E Recall |
|---------|---------------|---------------|-------------|-----------|
| A | Graph | 100% (candidate) | ~1% | **91.67%** |
| B | Graph | 100% (candidate) | ~5% | **100.00%** |
| C | Phase 1 | 0% | ~78% | **0.00%** |

## Key Insight: Complementarity

No single stream dominates all three patterns. Phase 1 misses A and B; Graph misses C.
The hybrid union is strictly necessary to achieve multi-pattern coverage.
