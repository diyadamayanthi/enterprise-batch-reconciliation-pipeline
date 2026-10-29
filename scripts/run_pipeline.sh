#!/bin/bash

# 1. Create runtime folders if they do not exist
mkdir -p incoming processed rejected reports database logs

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting batch reconciliation pipeline..." >> logs/pipeline.log

# 2. Execute Python pipeline located in src/
python3 src/pipeline.py >> logs/pipeline.log 2>&1

# 3. Check exit status
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline completed successfully." >> logs/pipeline.log
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline failed! Check logs." >> logs/pipeline.log
fi