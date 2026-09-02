# RiskOrbit — Investigation Agent Evaluation Report (Phase 2)

**Evaluation Scope:** Bounded multi-hop graph retrieval, evidence collection, latency, and tool reliability.

---

## 1. Investigation Agent Performance Benchmark

- **Average Case Investigation Latency:** 1005.26 ms
- **95th Percentile Latency:** 4843.19 ms
- **Tool Success Rate:** 100.0% (all bounded queries returned structured schema responses)
- **Tool Call Budget Limit:** Max 20 calls/case (average actual: 6.2 calls/case)
- **Max Traversal Depth:** Bounded at 2 hops

## 2. Golden Cases Benchmark Execution

| Case Code | Scenario | Expected | Individual Risk | Relationship Risk | Combined Risk | Ring Flagged | Latency |
|---|---|---|---|---|---|---|---|
| `CASE-GOLD-ABUSE-A` | pattern_a_shared_device | Abuse Ring | 0.2000 | 0.6196 | 0.4727 | **YES** | 7388.4 ms |
| `CASE-GOLD-ABUSE-B` | pattern_b_cross_merchant | Abuse Ring | 0.0000 | 0.3976 | 0.2584 | **YES** | 89.2 ms |
| `CASE-GOLD-ABUSE-C` | pattern_c_rotating_account | Abuse Ring | 0.0000 | 0.0000 | 0.0000 | **NO** | 51.3 ms |
| `CASE-GOLD-LEGIT-HOUSEHOLD` | household_sharing | Benign Infrastructure | 0.0000 | 0.6038 | 0.3925 | **YES** | 116.5 ms |
| `CASE-GOLD-LEGIT-NETWORK` | shared_network | Benign Infrastructure | 0.4286 | 0.6049 | 0.5432 | **YES** | 109.3 ms |
| `CASE-GOLD-LEGIT-SERIAL` | high_refund_customer | Benign Infrastructure | 0.4643 | 0.6067 | 0.5569 | **YES** | 115.0 ms |
| `CASE-GOLD-LEGIT-MERCHANT` | high_volume_merchant | Benign Infrastructure | 0.1667 | 0.5967 | 0.4462 | **YES** | 87.5 ms |
| `CASE-GOLD-LEGIT-MULTIDEV` | multi_device_customer | Benign Infrastructure | 0.1250 | 0.5957 | 0.4310 | **YES** | 84.9 ms |

## 3. Investigation Stopping Conditions Verification

- **Sufficient Evidence Stop:** Triggered when shared devices + coordinated refunds are verified.
- **Insufficient Evidence Stop:** Preserves low risk and records explicit uncertainty for isolated single-account interactions.
- **Budget Exhaustion Guard:** Traversal bounds prevent runaway recursive search.