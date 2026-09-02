# RiskOrbit — Phase 2 Diagnostic Failure Analysis

**Rigorous Root-Cause Failure Inspection on Held-Out Test Set**

---

## Failure Mode 1: 2-Hop Traversal Boundary Truncation on Pattern A
- **Symptom:** Pattern A rings spanning indirect 3-hop device links (Customer A → Device 1 → Customer B → Device 2 → Customer C) have only partial member recall.
- **Root Cause:** To ensure strict real-time performance (< 50ms), local case graph extraction is bounded at `max_hops=2`.
- **Trade-off Analysis:** Expanding to 3 hops increases memory and search latency by ~8x while increasing risk of false-positive bridge expansion across dense networks.

## Failure Mode 2: Sparse Transaction History in Burner Rings
- **Symptom:** New rotating burner accounts (Pattern C) with 0 prior transactions have no historical graph edges at the moment of their first transaction.
- **Mitigation:** Fallback to instrument and IP family linking (`instrument_synthetic_age` from Phase 1 combined with `accounts_per_ip`).

## Failure Mode 3: Tabular Feature Encoding Bottleneck
- **Symptom:** Passing graph summary statistics (`ring_customer_count`, `ring_device_count`) into a standard LightGBM tree does not capture structural isomorphism.
- **Scientific Finding:** Pure tabular GBDT models treat graph summary columns as independent scalar thresholds rather than traversing relational paths. The dedicated Investigation Agent solves this by constructing the explicit case graph and timeline directly.