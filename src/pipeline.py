import glob
import os
import shutil
import sqlite3
from datetime import datetime
import pandas as pd

DB_PATH = "database/enterprise_warehouse.db"


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table 1: Clean, validated transactions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_transactions (
            transaction_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            branch_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            transaction_timestamp TEXT NOT NULL,
            batch_date TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        )
    """)

    # Table 2: Quarantined exception log for audit & reconciliation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_quarantine_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_transaction_id TEXT,
            raw_account_id TEXT,
            branch_id TEXT,
            transaction_type TEXT,
            amount REAL,
            transaction_timestamp TEXT,
            rejection_reason TEXT NOT NULL,
            batch_date TEXT NOT NULL,
            logged_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def process_batches():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    files = glob.glob("incoming/batch_*.csv")

    if not files:
        print("[INFO] No inbound batch files available for ingestion.")
        return

    os.makedirs("reports", exist_ok=True)
    os.makedirs("processed", exist_ok=True)

    for file_path in files:
        filename = os.path.basename(file_path)
        batch_date = filename.replace("batch_", "").replace(".csv", "")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df = pd.read_csv(file_path)
        total_records = len(df)

        existing_db_ids = set(
            pd.read_sql(
                "SELECT transaction_id FROM fact_transactions", conn
            )["transaction_id"]
        )

        clean_rows = []
        quarantine_rows = []
        seen_batch_ids = set()

        for _, row in df.iterrows():
            t_id = row["transaction_id"]
            a_id = row["account_id"]
            branch = row["branch_id"]
            t_type = row["transaction_type"]
            amt = row["amount"]
            ts = row["transaction_timestamp"]

            # Rule 1: Non-null primary identifier
            if pd.isna(t_id) or str(t_id).strip() == "":
                quarantine_rows.append((
                    None,
                    a_id,
                    branch,
                    t_type,
                    amt,
                    ts,
                    "NULL_TRANSACTION_ID",
                    batch_date,
                    current_time,
                ))
                continue

            # Rule 2: Non-null account identifier
            if pd.isna(a_id) or str(a_id).strip() == "":
                quarantine_rows.append((
                    t_id,
                    None,
                    branch,
                    t_type,
                    amt,
                    ts,
                    "NULL_ACCOUNT_ID",
                    batch_date,
                    current_time,
                ))
                continue

            # Rule 3: Deduplication across batch & database
            if t_id in seen_batch_ids or t_id in existing_db_ids:
                quarantine_rows.append((
                    t_id,
                    a_id,
                    branch,
                    t_type,
                    amt,
                    ts,
                    "DUPLICATE_TRANSACTION_ID",
                    batch_date,
                    current_time,
                ))
                continue
            seen_batch_ids.add(t_id)

            # Rule 4: Numerical validity & non-negative rule
            try:
                amt_val = float(amt)
                if amt_val <= 0:
                    quarantine_rows.append((
                        t_id,
                        a_id,
                        branch,
                        t_type,
                        amt,
                        ts,
                        "NON_POSITIVE_AMOUNT",
                        batch_date,
                        current_time,
                    ))
                    continue
            except (ValueError, TypeError):
                quarantine_rows.append((
                    t_id,
                    a_id,
                    branch,
                    t_type,
                    amt,
                    ts,
                    "INVALID_NUMERIC_FORMAT",
                    batch_date,
                    current_time,
                ))
                continue

            # Valid Record
            clean_rows.append((
                t_id,
                a_id,
                branch,
                t_type,
                amt_val,
                ts,
                batch_date,
                current_time,
            ))

        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO fact_transactions 
            (transaction_id, account_id, branch_id, transaction_type, amount, transaction_timestamp, batch_date, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            clean_rows,
        )

        cursor.executemany(
            """
            INSERT INTO audit_quarantine_log 
            (raw_transaction_id, raw_account_id, branch_id, transaction_type, amount, transaction_timestamp, rejection_reason, batch_date, logged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            quarantine_rows,
        )
        conn.commit()

        # Generate Automated Multi-Tab Excel Reconciliation Workbook
        excel_path = f"reports/Reconciliation_Report_{batch_date}.xlsx"
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            # Sheet 1: Executive KPI Summary
            summary_df = pd.DataFrame({
                "KPI Metric": [
                    "Batch Processing Date",
                    "Total Records Received (Plan)",
                    "Successfully Ingested (Actual)",
                    "Quarantined Exceptions",
                    "Data Quality Attainment %",
                    "Total Settled Volume (INR)",
                ],
                "Value": [
                    batch_date,
                    total_records,
                    len(clean_rows),
                    len(quarantine_rows),
                    round((len(clean_rows) / total_records) * 100, 2),
                    round(sum(r[4] for r in clean_rows), 2),
                ],
            })
            summary_df.to_excel(
                writer, sheet_name="Reconciliation_Summary", index=False
            )

            # Sheet 2: Audit Quarantined Detail
            if quarantine_rows:
                quarantine_df = pd.DataFrame(
                    quarantine_rows,
                    columns=[
                        "Transaction_ID",
                        "Account_ID",
                        "Branch",
                        "Txn_Type",
                        "Amount",
                        "Timestamp",
                        "Rejection_Reason",
                        "Batch_Date",
                        "Logged_At",
                    ],
                )
                quarantine_df.to_excel(
                    writer, sheet_name="Audit_Exceptions", index=False
                )

        print(
            f"[COMPLETED] Processed {filename}: Ingested={len(clean_rows)} | Quarantined={len(quarantine_rows)}"
        )
        print(f"[EXCEL] Report generated at {excel_path}")

        # Export unified CSV extracts for Power BI & Tableau
        pd.read_sql("SELECT * FROM fact_transactions", conn).to_csv(
            "reports/bi_fact_transactions.csv", index=False
        )
        pd.read_sql("SELECT * FROM audit_quarantine_log", conn).to_csv(
            "reports/bi_audit_log.csv", index=False
        )

        shutil.move(file_path, f"processed/{filename}")

    conn.close()


if __name__ == "__main__":
    process_batches()