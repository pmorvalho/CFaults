#!/usr/bin/env bash
#Title			: gen_database.sh
#Usage			: bash gen_database.sh
#Author			: pmorvalho
#Date			: April 10, 2024
#Description		: Generates results.db database for CFaults' and BugAssists' FL results
#Notes			: 
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

if [[ -s results.db ]]; then
    echo "Removing old database"
    rm tcas.sql CPackIPAs.sql
fi    

echo "Generating new tables"
./get_sqlite3_table.sh -t > tcas.sql &
./get_sqlite3_table.sh -c > CPackIPAs.sql &

wait

# # creates and populates table programs
echo "Populating table TCAS"
time sqlite3 results.db < tcas.sql
echo
# # creates and populates table annotated_programs
echo "Populating table CPackIPAs"
time sqlite3 results.db < CPackIPAs.sql
echo

python3 data_2_plots.py $1

echo "CFaults' database is now populated!"
echo "Check newest plots at: database/plots"
