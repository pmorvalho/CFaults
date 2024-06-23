#!/usr/bin/env bash
#Title			: run_all.sh
#Usage			: bash run_all.sh
#Author			: pmorvalho
#Date			: June 20, 2024
#Description		: This scripts executes all the commands used for CFaults (FM 2024 paper) evaluation
#Notes			: 
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

chmod +x *.sh *.py
if [[ ! -d logs ]];
then
    mkdir logs
fi

TIMEOUT=3600
if [[ $1 != "" ]];
then
    TIMEOUT=$1
fi

# CFaults
echo
echo "------------------ CFaults ------------------"
echo
# run CFaults on TCAS
echo
echo "===== TCAS ====="
echo
time bash run_CFaults_on_benchmark.sh --tcas  --timeout $TIMEOUT | tee logs/CFaults-TCAS.log

# run CFaults on C-Pack-IPAs
echo
echo "===== C-Pack-IPAs ====="
echo
time bash run_CFaults_on_benchmark.sh  --timeout $TIMEOUT | tee logs/CFaults-CPackIPAs.log


# CFaults-Refined
echo
echo "------------------ CFaults-Refined ------------------"
echo
# run CFaults-Refined on TCAS
echo
echo "===== TCAS ====="
echo
time bash run_CFaults_on_benchmark.sh --tcas -ss  --timeout $TIMEOUT | tee logs/CFaults-TCAS.log

# run CFaults-Refined on C-Pack-IPAs
echo
echo "===== C-Pack-IPAs ====="
echo
time bash run_CFaults_on_benchmark.sh -ss  --timeout $TIMEOUT | tee logs/CFaults-CPackIPAs.log


# BugAssist
echo
echo "------------------ BugAssist ------------------"
echo
# run BugAssist on TCAS
echo
echo "===== TCAS ====="
echo
time bash run_BugAssist_on_benchmark.sh -t  --timeout $TIMEOUT | tee logs/BugAssist-TCAS.log

# run BugAssist on C-Pack-IPAs
echo
echo "===== C-Pack-IPAs ====="
echo
time bash run_BugAssist_on_benchmark.sh  --timeout $TIMEOUT | tee logs/BugAssist-CPackIPAs.log

# SNIPER
echo
echo "------------------ SNIPER ------------------"
echo
# run SNIPER on TCAS
echo
echo "===== TCAS ====="
echo
time bash run_SNIPER_on_benchmark.sh -t  --timeout $TIMEOUT | tee logs/SNIPER-TCAS.log

# run SNIPER on C-Pack-IPAs
echo
echo "===== C-Pack-IPAs ====="
echo
time bash run_SNIPER_on_benchmark.sh  --timeout $TIMEOUT | tee logs/SNIPER-CPackIPAs.log

echo
echo "------------------ DEALING WITH RESULTS ------------------"
echo

cd database

time ./gen_database.sh

cd ..

echo
echo
echo "CSV files can be found at 'database/csvs/'"
echo
echo "Plots can be found at 'database/plots/'"
echo
echo "SQLITE3 database can be found at 'database/results.db'"
echo
echo "------------------ THE END ------------------"
