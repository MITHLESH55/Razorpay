# RiskOrbit — Role-Based Access Control (RBAC) Matrix

## 1. Role Hierarchy & Levels

RiskOrbit enforces a 4-tier hierarchical access model:

| Level | Role Identifier | Display Title | Typical Persona |
| :---: | :--- | :--- | :--- |
| **1** | `VIEWER` | Audit & Compliance Officer | Regulatory Auditor, Executive, Model Risk Officer |
| **2** | `ANALYST` | Fraud Risk Analyst | Level-1/2 Operations Analyst, Triage Officer |
| **3** | `SENIOR_ANALYST` | Senior Risk Strategist | Policy Strategist, Ring Investigator, Senior Reviewer |
| **4** | `ADMIN` | Chief Information Security Officer | Risk Engineering Lead, CISO, Ops Administrator |

---

## 2. Granular Capability & Action Matrix

| Operation / Feature | VIEWER (L1) | ANALYST (L2) | SENIOR_ANALYST (L3) | ADMIN (L4) |
| :--- | :---: | :---: | :---: | :---: |
| **Command Center Overview (`/overview`)** | Read-Only | Full Access | Full Access | Full Access |
| **Risk Queue Search & Triage (`/queue`)** | Read-Only | Full Access | Full Access | Full Access |
| **Case Subgraph & Evidence (`/cases/{id}`)** | Read-Only | Full Access | Full Access | Full Access |
| **Low-Impact Action Approval (`ALLOW`, `2FA`, `DELAY`)** | ❌ (403) | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **High-Impact Action Approval (`BLOCK`, `RESTRICT`, `FREEZE`)** | ❌ (403) | ❌ (403) | ✅ Allowed | ✅ Allowed |
| **Action Override & Recommendation Edit** | ❌ (403) | ❌ (403) | ✅ Allowed | ✅ Allowed |
| **Analyst Ground-Truth Adjudication (`/feedback`)** | ❌ (403) | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **Counterfactual Policy Simulation (`/simulate`)** | ❌ (403) | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **Immutable Audit Log Inspection (`/audit`)** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **Held-Out Evaluation & Release Manifest (`/evaluation`, `/manifest`)** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **Distribution Drift Telemetry (`/drift`)** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **System Controls: Shadow Mode (`/controls`)** | ❌ (403) | ❌ (403) | ❌ (403) | ✅ Allowed |
| **System Controls: Emergency Kill Switch (`/controls`)** | ❌ (403) | ❌ (403) | ❌ (403) | ✅ Allowed |

---

## 3. High-Impact vs. Low-Impact Action Classification

```
HIGH_IMPACT_ACTIONS = {
    "BLOCK_TRANSACTION",
    "RESTRICT_ACCOUNT",
    "FREEZE_RING",
    "HARD_BLOCK_ACCOUNT"
}

LOW_IMPACT_ACTIONS = {
    "ALLOW",
    "STEP_UP_2FA",
    "DELAY_SETTLEMENT",
    "MANUAL_REVIEW",
    "MONITOR"
}
```

- High-impact actions directly disrupt user transactions or freeze entity funds. Strict four-eyes / senior analyst authorization (`SENIOR_ANALYST` or `ADMIN`) is required.
- Low-impact actions introduce mild friction (step-up 2FA) or temporary analytical holds, accessible to all operational analysts.
- `VIEWER` users are strictly forbidden from taking any mutating action on cases, feedback, or system controls.

---

## 4. Pre-Configured Enterprise Demo Personas

| Persona ID | Name | Role | Email | Capabilities Summary |
| :--- | :--- | :--- | :--- | :--- |
| `analyst_01` | Sarah Chen | `ANALYST` | `sarah.chen@riskorbit.internal` | Queue triage, low-impact approvals, feedback adjudication |
| `senior_analyst_01` | Marcus Vance | `SENIOR_ANALYST` | `marcus.vance@riskorbit.internal` | High-impact approvals, overrides, counterfactual workbench |
| `admin_01` | Elena Rostova | `ADMIN` | `elena.rostova@riskorbit.internal` | Kill switch controls, safe mode, shadow mode, audit oversight |
| `viewer_01` | Audit Officer | `VIEWER` | `audit.read@riskorbit.internal` | Read-only compliance audit, metrics, PSI drift verification |
