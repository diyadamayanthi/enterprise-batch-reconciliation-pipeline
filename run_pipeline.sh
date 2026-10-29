#!/bin/bash

# 1. Create runtime folders if they do not exist
mkdir -p data/incoming data/quarantine data/processed logs

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting batch reconciliation pipeline..." >> logs/pipeline.log

# 2. Run your existing Python pipeline and log output
python3 pipeline.py >> logs/pipeline.log 2>&1

# 3. Check if the script finished successfully
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline executed successfully." >> logs/pipeline.log
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline failed! Check logs." >> logs/pipeline.log
fi
