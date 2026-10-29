import os
import random
from datetime import datetime, timedelta
import pandas as pd


def generate_daily_batch(num_records=150):
    os.makedirs("incoming", exist_ok=True)
    batch_date = datetime.now().strftime("%Y%m%d")
    filename = f"incoming/batch_{batch_date}.csv"

    branches = [
        "BR_KORAMANGALA",
        "BR_INDIRANAGAR",
        "BR_WHITEFIELD",
        "BR_JAYANAGAR",
        "BR_MG_ROAD",
    ]
    txn_types = ["DEPOSIT", "WITHDRAWAL", "LOAN_REPAYMENT", "WIRE_TRANSFER"]

    records = []
    base_time = datetime.now() - timedelta(hours=12)

    for i in range(1, num_records + 1):
        txn_id = f"TXN_{batch_date}_{1000 + i}"
        account_id = f"ACC_{random.randint(1001, 1075)}"
        branch = random.choice(branches)
        txn_type = random.choice(txn_types)
        amount = round(random.uniform(250.0, 85000.0), 2)
        txn_time = (base_time + timedelta(minutes=i * 4)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        records.append(
            [txn_id, account_id, branch, txn_type, amount, txn_time]
        )

    # Inject specific anomalies to test the pipeline rules:
    # 1. Null Primary Key
    records[5][0] = None
    # 2. Non-positive / Negative Currency
    records[14][4] = -15000.00
    # 3. Duplicate Transaction ID
    records[28][0] = records[10][0]
    # 4. Null Account ID
    records[42][1] = None

    df = pd.DataFrame(
        records,
        columns=[
            "transaction_id",
            "account_id",
            "branch_id",
            "transaction_type",
            "amount",
            "transaction_timestamp",
        ],
    )
    df.to_csv(filename, index=False)
    print(f"[OK] Inbound batch generated: {filename} ({len(df)} records)")


if __name__ == "__main__":
    generate_daily_batch()