# RiskOrbit — Data Quality Report

**Validation status:** ✅ PASSED
**Errors:** 0
**Warnings:** 1

---

## Entity Counts

| Entity | Count |
|--------|------:|
| Customers | 22,000 |
| Merchants | 1,100 |
| Devices | 13,000 |
| IP Entities | 9,000 |
| Instruments | 18,000 |

## Event Counts

| Table | Count |
|-------|------:|
| Orders | 190,615 |
| Transactions | 190,618 |
| Refunds | 36,128 |

## Class Distribution

- **Transaction abuse rate:** 0.0102 (1.02%)
- **Abuse rings:** 160

## Hard Negative Distribution

- **high_volume_merchant:** 63,110
- **shared_network:** 8,011
- **high_refund_customer:** 7,729
- **household_sharing:** 6,025
- **multi_device_customer:** 4,111

## Errors

- None ✅

## Warnings

- ⚠️ refunds: 2 refunds exceed transaction amount (minor tolerance)