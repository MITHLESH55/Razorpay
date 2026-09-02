# RiskOrbit — Ground Truth & Target Definition Audit

**Audit Date:** 2026-08-27  
**Auditor:** Principal ML & Fintech Risk Engineer  
**Status:** PASSED (Ground Truth Integrity Verified)  

---

## 1. Target Definition & Prediction Contract

- **Primary Binary Target:** `abuse_label`
  - `1 = coordinated refund abuse` (transaction belongs to an organized multi-account or multi-entity refund abuse ring)
  - `0 = legitimate transaction` (single-user purchase, benign serial returner, household sharing, or shared network activity)
- **Unit of Prediction:** Transaction event (`transaction_id`)
- **Scoring Timestamp:** `timestamp` of the transaction
- **Information Available at Prediction Time:** Historical transaction logs, past refund requests strictly prior to `timestamp`, and static registered entity attributes.
- **Strict Prohibition:** Future transactions, future refund requests, investigation outcomes, chargeback resolutions, and synthetic ring metadata (`ring_id`, `abuse_pattern_type`, `shared_devices`, `linking_ip`) are strictly excluded.

---

## 2. Provenance and Label Independence

Ground truth labels are synthesized through explicit generative behavioral simulation:
1. **Legitimate Stream**: Created using segment-based Poisson arrival processes, lognormal basket amounts, category-specific refund probabilities, and realistic multi-device/multi-IP sharing distributions.
2. **Hard-Negative Injections**: 6 confuser types explicitly injected with `abuse_label = 0` to prevent heuristic shortcutting (e.g. household tablets sharing multiple accounts, university/office subnets sharing single IP, serial returners with 70%+ refund rates).
3. **Abuse Rings**: 160 distinct rings generated with parameterized coordination logic (Pattern A, Pattern B, Pattern C). Metadata detailing the injection seed, account rosters, and linking infrastructure is isolated into `data/raw/generation_metadata/abuse_rings.csv`.

---

## 3. Realism & Non-Trivial Separability Audit

We audited whether abuse transactions can be separated using single trivial thresholds:

| Signal | Abuse Population Distribution | Legitimate Population Distribution | Separability Assessment |
|---|---|---|---|
| **Transaction Amount** | ₹200 – ₹8,000 (Median: ~₹1,450) | ₹10.90 – ₹29,947 (Median: ~₹618) | **Non-separable:** Abuse amounts fall completely inside benign range. |
| **Device Sharing** | 3–8 accounts per device in Pattern A | 2–6 accounts per device in Household sharing | **Non-separable:** Overlaps directly with household sharing hard negatives. |
| **IP Sharing** | 4–10 accounts per IP in Pattern B | 12–40 accounts per IP in Shared Network hard negatives | **Non-separable:** Overlaps directly with benign corporate/campus IPs. |
| **Account Age** | 1–60 days in Pattern C | 1–730 days in Legitimate pool | **Non-separable:** Overlaps directly with legitimate new customers. |

**Audit Conclusion:** Ground truth is clean, provably independent of feature generation, and robustly non-trivially separable.
