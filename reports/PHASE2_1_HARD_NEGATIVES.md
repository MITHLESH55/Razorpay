# PHASE 2.1 HARD NEGATIVE ANALYSIS

Overall FPR: **76.23%** | Overall FP Cost: **Rs.2,804,750**

## Hard Negative Performance Table

| Category | Txns | Customers | In Budget | FP Customers | FPR | FP Cost |
|----------|------|-----------|-----------|-------------|-----|---------|
| High Refund Customer | 1,117 | 366 | 136 | 281 | 73.86% | Rs.107,250 |
| High-Volume Merchant | 9,558 | 7,769 | 495 | 4845 | 62.44% | Rs.775,840 |
| Household Sharing | 905 | 568 | 34 | 442 | 78.01% | Rs.91,780 |
| Multi Device Customer | 601 | 279 | 8 | 259 | 93.18% | Rs.72,800 |
| Shared Network | 1,192 | 876 | 63 | 714 | 81.21% | Rs.125,840 |
| General Legitimate | 14,928 | 7,239 | 599 | 5467 | 84.06% | Rs.1,631,240 |

## Category Definitions and Mitigations

### Household Sharing
Family members sharing a device or home IP. Graph creates sharing edges, but their low refund rates
and long tenure distinguish them. Mitigation: hubness penalty reduces high-degree shared device edges.

### Shared Network
Corporate/university network IP sharing. Mitigation: IP edges penalized more than device; rings
require coordinated merchant targeting beyond incidental IP sharing.

### Serial Returner
Legitimate high return-rate customer (e.g., fashion e-commerce). Mitigation: Phase 1 threshold 0.20
filters many legitimate serial returners. Investigation requires ring membership (>=2 accounts).

### Multi-Device Legitimate
Personal multi-device use (phone, tablet, laptop). Mitigation: hubness penalty limits contribution;
ring detection requires shared devices AND coordinated refund timing.

### High-Volume Merchant
Merchant with many refund transactions. Mitigation: ring detection traverses customer->device/IP edges;
merchant nodes do not initiate ring membership.
