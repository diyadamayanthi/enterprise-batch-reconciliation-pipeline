# Enterprise Automated Batch Fulfillment & Reconciliation Pipeline

An end-to-end operational analytics pipeline designed to process daily financial batch transactions across regional branch networks, track fulfillment variances against aggregate baseline benchmarks, and deliver cross-filtered executive visibility.

🔗 **[View Interactive Tableau Public Dashboard](https://public.tableau.com/authoring/EnterpriseSettlementReconciliationOperationsDashboard/Dashboard1#1)**

---

## Dashboard Preview

![Dashboard Preview](https://github.com/diyadamayanthi/enterprise-batch-reconciliation-pipeline/blob/main/dashboard_preview.png.png)

---

## Business Objective & Problem Statement
High-volume retail banking batch pipelines require daily reconciliation between branch-level transaction inflows (deposits, wire transfers, loan repayments) and operational settlement thresholds. This project establishes an automated monitoring mechanism to identify anomalous branch variance, measure transaction type composition, and track intraday settlement velocity.

---

## Technical Architecture & Tools
* **BI & Visualization:** Tableau Public (Web Authoring)
* **Analytical Formulations:** Fixed Level of Detail (LOD) Expressions, Global Cross-Filtering Actions
* **Data Layer:** `bi_fact_transactions.csv` (Batch transaction ledger with timestamps, status, amount, and branch dimensions)

---

## Key Metrics & Analytical Features
* **Branch Settlement Performance:** Compares total volume across 5 regional branches against an enterprise baseline benchmark using a Fixed LOD target.
* **Transaction Mix Breakdown:** Real-time visibility into the distribution of Deposits, Withdrawals, Wire Transfers, and Loan Repayments.
* **Intraday Settlement Velocity:** Time-series tracking of batch processing across intraday execution windows.
* **Dynamic Cross-Filtering:** Interactive drill-down filtering across branches and categories across the entire view.

---

## Calculations & Logic
* **Branch Baseline Benchmark (LOD Expression):**
  ```tableau
  { FIXED : AVG({ FIXED [Branch Id] : SUM([Amount]) }) }
