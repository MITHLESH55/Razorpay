# PHASE 2.1 FAILURE ANALYSIS

## Miss Summary

| Pattern | Total | Confirmed | Missed |
|---------|-------|-----------|--------|
| Pattern A (Device/Coord) | 12 | 11 | **1** |
| Pattern B (IP-sharing) | 4 | 4 | **0** |
| Pattern C (Refund-burst) | 8 | 0 | **8** |
| **Total** | **24** | **15** | **9** |

## Root-Cause Analysis

### Pattern A Misses

1. **Budget rank exclusion:** 12,573 candidates compete for K=1000 slots. Pattern A rings with low-strength edges (hubness-penalized shared devices) rank below the budget cutoff.
2. **Hubness over-correction:** Devices shared by >10 customers receive near-zero edge weight. An abuse ring on a crowded device has diluted structural signal.
3. **Point-in-time boundary:** Late-starting rings (primary activity after as_of_time) have insufficient historical signal.

### Pattern B Misses

1. **IP penalty:** IP edges are penalized more aggressively than device edges (NAT/carrier sharing risk). Low-activity rings via carrier NAT approach zero edge strength.
2. **Budget competition:** Pattern B competes with 12,573 union candidates for K=1000 slots.

### Pattern C Misses

1. **Phase 1 ceiling:** Graph stream gives 0% Pattern C coverage. Phase 1 recall is bounded at 28.62%. Members scoring below 0.20 threshold generate no Phase 1 candidates.
2. **Sparse abusers:** Rings with 1-2 refunds per customer over many months have low refund-velocity features.

## Systematic Gaps

| Gap | Mechanism | Severity |
|-----|-----------|---------|
| Budget exclusion at K=1000 | 11,573 candidates not investigated | High |
| Phase 1 recall ceiling on Pattern C | Frozen model | Medium |
| Hubness penalty over-correction | High-degree device nodes penalized | Medium |
| IP penalty too aggressive | NAT/carrier IPs filtered | Low |
