"""
RiskOrbit — Data Validator
Performs referential integrity checks, business rule validations,
anomaly detection, and generates the DATA_QUALITY_REPORT.

All validations are deterministic and parameterless (no random decisions).
Failures are logged as errors; warnings are informational.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validates the synthetic ecosystem data for integrity.

    Usage:
        validator = DataValidator(customers, merchants, devices,
                                  ip_entities, instruments,
                                  orders, transactions, refunds)
        report = validator.run()
        validator.save_report(report, output_path)
    """

    def __init__(
        self,
        customers: pd.DataFrame,
        merchants: pd.DataFrame,
        devices: pd.DataFrame,
        ip_entities: pd.DataFrame,
        instruments: pd.DataFrame,
        orders: pd.DataFrame,
        transactions: pd.DataFrame,
        refunds: pd.DataFrame,
    ) -> None:
        self.customers = customers
        self.merchants = merchants
        self.devices = devices
        self.ip_entities = ip_entities
        self.instruments = instruments
        self.orders = orders
        self.transactions = transactions
        self.refunds = refunds
        self.errors: list[str] = []
        self.warnings: list[str] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Run all validations and return a summary report dict."""
        logger.info("Starting data validation …")
        self._check_unique_ids()
        self._check_referential_integrity()
        self._check_temporal_consistency()
        self._check_refund_amounts()
        self._check_non_negative_amounts()
        self._check_ground_truth_completeness()
        self._check_expected_sizes()
        stats = self._compute_stats()

        report = {
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": stats,
            "passed": len(self.errors) == 0,
        }
        if self.errors:
            logger.error("Validation FAILED: %d errors found", len(self.errors))
            for e in self.errors:
                logger.error("  ERROR: %s", e)
        else:
            logger.info("Validation PASSED with %d warnings", len(self.warnings))
        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _err(self, msg: str) -> None:
        self.errors.append(msg)

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning(msg)

    def _check_unique_ids(self) -> None:
        checks = [
            (self.customers, "customer_id", "customers"),
            (self.merchants, "merchant_id", "merchants"),
            (self.devices, "device_id", "devices"),
            (self.ip_entities, "ip_id", "ip_entities"),
            (self.instruments, "instrument_id", "instruments"),
            (self.orders, "order_id", "orders"),
            (self.transactions, "transaction_id", "transactions"),
            (self.refunds, "refund_id", "refunds"),
        ]
        for df, col, name in checks:
            if col not in df.columns:
                self._err(f"{name}: missing column {col}")
                continue
            n_dup = df[col].duplicated().sum()
            if n_dup > 0:
                self._err(f"{name}: {n_dup} duplicate {col} values")

    def _check_referential_integrity(self) -> None:
        # Transactions must reference valid orders, customers, merchants
        txn_order_ids = set(self.transactions["order_id"].dropna())
        ord_ids = set(self.orders["order_id"].dropna())
        orphan_txn = txn_order_ids - ord_ids
        if orphan_txn:
            self._err(f"transactions: {len(orphan_txn)} order_ids not in orders table")

        txn_cust_ids = set(self.transactions["customer_id"].dropna())
        cust_ids = set(self.customers["customer_id"].dropna())
        # Pattern C generates ring customers not in the main table — allow these
        unmatched_custs = txn_cust_ids - cust_ids
        if len(unmatched_custs) > 5000:
            self._warn(
                f"transactions: {len(unmatched_custs)} customer_ids not in customers table "
                "(expected for Pattern C ring accounts)"
            )

        # Refunds must reference valid transactions
        ref_txn_ids = set(self.refunds["transaction_id"].dropna())
        txn_ids = set(self.transactions["transaction_id"].dropna())
        orphan_ref = ref_txn_ids - txn_ids
        if orphan_ref:
            self._err(f"refunds: {len(orphan_ref)} transaction_ids not in transactions table")

    def _check_temporal_consistency(self) -> None:
        # Refund requested_at must be >= transaction timestamp
        if len(self.refunds) == 0:
            return
        merged = self.refunds.merge(
            self.transactions[["transaction_id", "timestamp"]],
            on="transaction_id", how="left",
        )
        if "timestamp" not in merged.columns:
            return
        bad = merged[
            merged["refund_requested_at"].notna()
            & merged["timestamp"].notna()
            & (pd.to_datetime(merged["refund_requested_at"], format="mixed") < pd.to_datetime(merged["timestamp"], format="mixed"))
        ]
        if len(bad) > 0:
            self._err(f"refunds: {len(bad)} refunds requested before payment timestamp")

        # Refund processed_at >= refund_requested_at
        bad_proc = self.refunds[
            self.refunds["refund_processed_at"].notna()
            & self.refunds["refund_requested_at"].notna()
            & (
                pd.to_datetime(self.refunds["refund_processed_at"], format="mixed")
                < pd.to_datetime(self.refunds["refund_requested_at"], format="mixed")
            )
        ]
        if len(bad_proc) > 0:
            self._err(f"refunds: {len(bad_proc)} processed before requested")

    def _check_refund_amounts(self) -> None:
        if len(self.refunds) == 0:
            return
        merged = self.refunds.merge(
            self.transactions[["transaction_id", "amount"]],
            on="transaction_id", how="left",
        )
        if "amount" not in merged.columns:
            return
        bad = merged[
            merged["refund_amount"].notna()
            & merged["amount"].notna()
            & (merged["refund_amount"] > merged["amount"] * 1.01)  # 1% tolerance
        ]
        if len(bad) > 0:
            self._warn(f"refunds: {len(bad)} refunds exceed transaction amount (minor tolerance)")

    def _check_non_negative_amounts(self) -> None:
        for df, col, name in [
            (self.transactions, "amount", "transactions"),
            (self.refunds, "refund_amount", "refunds"),
            (self.orders, "amount", "orders"),
        ]:
            if col not in df.columns:
                continue
            bad = (df[col] < 0).sum()
            if bad > 0:
                self._err(f"{name}: {bad} negative {col} values")

    def _check_ground_truth_completeness(self) -> None:
        for df, name in [
            (self.transactions, "transactions"),
            (self.orders, "orders"),
        ]:
            if "abuse_label" not in df.columns:
                self._err(f"{name}: missing abuse_label column")
                continue
            null_labels = df["abuse_label"].isna().sum()
            if null_labels > 0:
                self._err(f"{name}: {null_labels} null abuse_label values")

    def _check_expected_sizes(self) -> None:
        if len(self.transactions) < 50_000:
            self._warn(f"transactions count {len(self.transactions)} < expected 50,000")
        if len(self.customers) < 10_000:
            self._warn(f"customers count {len(self.customers)} < expected 10,000")

    def _compute_stats(self) -> dict:
        txn_abuse_rate = (
            self.transactions["abuse_label"].mean()
            if "abuse_label" in self.transactions.columns else None
        )
        ring_ids = (
            self.transactions[self.transactions["ring_id"].notna() & (self.transactions["ring_id"] != "")]
            ["ring_id"].nunique()
            if "ring_id" in self.transactions.columns else None
        )
        hn_counts = {}
        if "hard_negative_type" in self.transactions.columns:
            hn_counts = (
                self.transactions[self.transactions["hard_negative_type"] != ""]
                ["hard_negative_type"].value_counts().to_dict()
            )

        return {
            "n_customers": len(self.customers),
            "n_merchants": len(self.merchants),
            "n_devices": len(self.devices),
            "n_ip_entities": len(self.ip_entities),
            "n_instruments": len(self.instruments),
            "n_orders": len(self.orders),
            "n_transactions": len(self.transactions),
            "n_refunds": len(self.refunds),
            "txn_abuse_rate": float(txn_abuse_rate) if txn_abuse_rate is not None else None,
            "n_abuse_rings": ring_ids,
            "hard_negative_counts": hn_counts,
            "n_errors": len(self.errors),
            "n_warnings": len(self.warnings),
        }

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def save_report(self, report: dict, output_path: Path) -> None:
        """Write DATA_QUALITY_REPORT.md."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stats = report["stats"]
        lines = [
            "# RiskOrbit — Data Quality Report",
            "",
            f"**Validation status:** {'✅ PASSED' if report['passed'] else '❌ FAILED'}",
            f"**Errors:** {len(report['errors'])}",
            f"**Warnings:** {len(report['warnings'])}",
            "",
            "---",
            "",
            "## Entity Counts",
            "",
            f"| Entity | Count |",
            f"|--------|------:|",
            f"| Customers | {stats['n_customers']:,} |",
            f"| Merchants | {stats['n_merchants']:,} |",
            f"| Devices | {stats['n_devices']:,} |",
            f"| IP Entities | {stats['n_ip_entities']:,} |",
            f"| Instruments | {stats['n_instruments']:,} |",
            "",
            "## Event Counts",
            "",
            f"| Table | Count |",
            f"|-------|------:|",
            f"| Orders | {stats['n_orders']:,} |",
            f"| Transactions | {stats['n_transactions']:,} |",
            f"| Refunds | {stats['n_refunds']:,} |",
            "",
            "## Class Distribution",
            "",
            f"- **Transaction abuse rate:** {stats['txn_abuse_rate']:.4f} "
            f"({stats['txn_abuse_rate']*100:.2f}%)" if stats["txn_abuse_rate"] is not None else "",
            f"- **Abuse rings:** {stats['n_abuse_rings']}",
            "",
            "## Hard Negative Distribution",
            "",
        ]
        for hn_type, count in (stats.get("hard_negative_counts") or {}).items():
            lines.append(f"- **{hn_type}:** {count:,}")

        lines += [
            "",
            "## Errors",
            "",
        ]
        if report["errors"]:
            for e in report["errors"]:
                lines.append(f"- ❌ {e}")
        else:
            lines.append("- None ✅")

        lines += [
            "",
            "## Warnings",
            "",
        ]
        if report["warnings"]:
            for w in report["warnings"]:
                lines.append(f"- ⚠️ {w}")
        else:
            lines.append("- None ✅")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Data quality report saved to %s", output_path)
