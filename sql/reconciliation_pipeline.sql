-- ============================================================================
-- Enterprise Automated Batch Fulfillment & Reconciliation Pipeline
-- Script: reconciliation_pipeline.sql
-- Description: Ingests raw batch transactions, applies cleansing/validation,
--              executes branch reconciliation, and generates bi_fact_transactions.
-- ============================================================================

-- 1. Create Staging Table for Raw Ingestion
CREATE TABLE IF NOT EXISTS stg_raw_transactions (
    raw_record_id VARCHAR(64) PRIMARY KEY,
    transaction_id VARCHAR(50),
    account_id VARCHAR(50),
    branch_id VARCHAR(50),
    transaction_type VARCHAR(50),
    amount NUMERIC(15, 2),
    raw_timestamp VARCHAR(50),
    raw_batch_date VARCHAR(50),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Cleanse, Cast, and Validate Raw Batch Records
CREATE TABLE IF NOT EXISTS clean_stg_transactions AS
SELECT
    TRIM(transaction_id) AS transaction_id,
    TRIM(account_id) AS account_id,
    UPPER(TRIM(branch_id)) AS branch_id,
    UPPER(TRIM(transaction_type)) AS transaction_type,
    ABS(CAST(amount AS NUMERIC(15, 2))) AS amount,
    CAST(raw_batch_date AS DATE) AS batch_date,
    CAST(raw_timestamp AS TIMESTAMP) AS transaction_timestamp,
    CURRENT_TIMESTAMP AS processed_at,
    CASE 
        WHEN amount <= 0 OR amount IS NULL THEN 'REJECTED_INVALID_AMOUNT'
        WHEN branch_id IS NULL THEN 'REJECTED_MISSING_BRANCH'
        WHEN transaction_type NOT IN ('DEPOSIT', 'WITHDRAWAL', 'WIRE_TRANSFER', 'LOAN_REPAYMENT') THEN 'REJECTED_INVALID_TYPE'
        ELSE 'VALIDATED'
    END AS validation_status
FROM stg_raw_transactions;

-- 3. Branch Daily Reconciliation & Exception Ledger
-- Detects anomalous daily branch deviations against the regional historical mean
CREATE TABLE IF NOT EXISTS rpt_branch_reconciliation_summary AS
WITH daily_branch_totals AS (
    SELECT
        branch_id,
        batch_date,
        COUNT(transaction_id) AS total_transactions,
        SUM(amount) AS total_settlement_amount,
        AVG(amount) AS avg_transaction_size
    FROM clean_stg_transactions
    WHERE validation_status = 'VALIDATED'
    GROUP BY branch_id, batch_date
),
benchmark_calc AS (
    SELECT
        branch_id,
        batch_date,
        total_transactions,
        total_settlement_amount,
        AVG(total_settlement_amount) OVER () AS enterprise_benchmark_target,
        ROUND(
            (total_settlement_amount - AVG(total_settlement_amount) OVER ()) 
            / NULLIF(AVG(total_settlement_amount) OVER (), 0) * 100, 
            2
        ) AS variance_pct
    FROM daily_branch_totals
)
SELECT 
    branch_id,
    batch_date,
    total_transactions,
    total_settlement_amount,
    enterprise_benchmark_target,
    variance_pct,
    CASE 
        WHEN variance_pct < -20.00 THEN 'UNDERPERFORMING_SETTLEMENT'
        WHEN variance_pct > 25.00 THEN 'ANOMALOUS_SURGE'
        ELSE 'WITHIN_THRESHOLD'
    END AS reconciliation_status
FROM benchmark_calc;

-- 4. Publish Curated Fact Table for Tableau Consumption (bi_fact_transactions.csv)
CREATE TABLE IF NOT EXISTS bi_fact_transactions AS
SELECT
    t.transaction_id,
    t.account_id,
    t.branch_id,
    t.transaction_type,
    t.amount,
    t.batch_date,
    t.transaction_timestamp,
    t.processed_at AS ingested_at
FROM clean_stg_transactions t
WHERE t.validation_status = 'VALIDATED';
