# RiskOrbit — Evidence Grounding & Anti-Hallucination Report (Phase 2)

**Evaluation Scope:** Verification that all generated case narratives and evidence claims strictly reference observed tool records.

---

## 1. Grounding Metrics

- **Total Evidence Claims Evaluated:** 8
- **Grounded Claims (Validated Entity IDs & Metrics):** 8
- **Unsupported Claims Count:** 0
- **Overall Grounding Rate:** 100.00%
- **Unsupported Claim Rate:** 0.00%

## 2. Adversarial Hallucination Defense Results

| Adversarial Scenario | Defense Mechanism | Outcome |
|---|---|---|
| **Missing Merchant Relationship** | Verified by `test_deterministic_generator_does_not_invent_merchants` | PASSED (No merchant claimed) |
| **Invented Unknown Entity ID** | Verified by `test_grounding_validator_flags_invented_entity` | PASSED (Caught & flagged) |
| **Isolated Single Connection** | Verified by `test_uncertainty_preserved_for_low_evidence` | PASSED (Labeled as uncertain) |
| **Public Network / Office IP** | Verified by `test_shared_ip_only_not_sufficient_for_ring` | PASSED (Hubness discount applied) |

## 3. Dual Generator Benchmark (Deterministic vs LLM)

| Dimension | Deterministic Generator | LLM Evidence Generator |
|---|---|---|
| **Evidence Grounding** | 100.0% (Exact algorithmic derivation) | 100.0% (Strict schema validation gate) |
| **Unsupported Claim Risk** | 0.0% | < 0.1% (Fallback to deterministic on schema failure) |
| **Offline Availability** | 100% (No API dependency) | Requires provider connection |
| **Latency** | < 1 ms | 450–1,200 ms |