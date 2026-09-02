# RiskOrbit — Graph Data Quality & Hubness Report (Phase 2)

**Date:** 2026-08-27  
**Graph Build Latency:** 34.199 seconds  
**Observation Cutoff:** 2024-12-30T23:53:10  

---

## 1. Graph Scale & Entity Breakdown

- **Total Nodes:** 63,212
- **Total Edges:** 629,955
- **Average Degree:** 19.93
- **Median Degree:** 12.0
- **95th Percentile Degree:** 59.0
- **99th Percentile Degree:** 124.0
- **Max Node Degree:** 2,912
- **Mean Edge Strength:** 0.0786

### Nodes by Entity Type:

| Entity Type | Count | % of Graph Nodes |
|---|---|---|
| **CUSTOMER** | 22,113 | 34.98% |
| **INSTRUMENT** | 17,999 | 28.47% |
| **DEVICE** | 13,000 | 20.57% |
| **IP** | 9,000 | 14.24% |
| **MERCHANT** | 1,100 | 1.74% |

### Edges by Relationship Type:

| Relationship Type | Edge Count | % of Total Edges |
|---|---|---|
| **CUSTOMER_USED_INSTRUMENT** | 182,370 | 28.95% |
| **CUSTOMER_PLACED_ORDER** | 178,248 | 28.30% |
| **CUSTOMER_USED_DEVICE** | 166,895 | 26.49% |
| **CUSTOMER_CONNECTED_IP** | 102,442 | 16.26% |

---

## 2. Hubness Analysis & Extreme Degree Distribution

To prevent common shared infrastructure (e.g. high-volume merchants, ISP gateways, corporate subnets) from creating artificial ring clusters, the graph engine applies **inverse popularity hubness discounting**.

### Top 15 Highest-Degree Entities in Payment Graph:

| Entity ID | Entity Type | Observed Degree (Connected Entities) | Hubness Normalization Impact |
|---|---|---|---|
| `MER_00000652` | **MERCHANT** | 2,912 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000329` | **MERCHANT** | 2,890 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000540` | **MERCHANT** | 2,774 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000644` | **MERCHANT** | 2,712 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000207` | **MERCHANT** | 2,676 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000980` | **MERCHANT** | 2,620 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000167` | **MERCHANT** | 2,607 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000182` | **MERCHANT** | 2,593 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000610` | **MERCHANT** | 2,555 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000055` | **MERCHANT** | 2,484 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000224` | **MERCHANT** | 2,467 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000547` | **MERCHANT** | 2,380 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000477` | **MERCHANT** | 2,329 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000121` | **MERCHANT** | 2,174 | Discounted (Legitimate high-throughput retail catalog) |
| `MER_00000985` | **MERCHANT** | 2,095 | Discounted (Legitimate high-throughput retail catalog) |

---

## 3. Data Quality Verdict

- **Zero Orphan References:** All edges reference validated entities in the underlying payment store.
- **Temporal Monotonicity:** Point-in-time filter correctly isolates events $\le T$.
- **Hub Resistance:** Merchants and high-degree IPs do not cause artificial graph explosion due to localized subgraphs and hubness penalties.