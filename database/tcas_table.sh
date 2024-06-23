#!/usr/bin/env bash
#Title			: tcas_table.sh
#Usage			: bash tcas_table.sh
#Author			: pmorvalho
#Date			: January 29, 2024
#Description		: Prints a SQL script to populate table TCAS.
#Notes			: 
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

echo '''DROP TABLE IF EXISTS tcas;
CREATE TABLE tcas (
    program_id VARCHAR (255),
    fault_loc_method VARCHAR (255),
    state VARCHAR (255) NOT NULL,
    time REAL,
    memory REAL,
    cbmc_time REAL,
    cbmc_memory REAL,
    oracle_time REAL,
    oracle_memory REAL,
    cbmc_2nd_call_time REAL,
    cbmc_2nd_call_memory REAL,
    opt_cost INT,
    num_bugs INT,
    num_faults_evaluated INT,
    num_mcses INT,
    num_diagnoses INT,
    second_step BOOLEAN,
    ss_cbmc_time REAL,
    ss_cbmc_memory REAL,
    ss_oracle_time REAL,
    ss_oracle_memory REAL,
    ss_cbmc_2nd_call_time REAL,
    ss_cbmc_2nd_call_memory REAL,
    ss_opt_cost INT,    
    ss_num_bugs INT,
    ss_num_diagnoses INT,
    PRIMARY KEY (program_id, fault_loc_method)
    );'''

echo '''INSERT INTO tcas (
    program_id,
    fault_loc_method,
    state,
    time, 
    memory,
    cbmc_time,
    cbmc_memory,
    oracle_time,
    oracle_memory,
    cbmc_2nd_call_time,
    cbmc_2nd_call_memory,
    opt_cost,    
    num_bugs,
    num_faults_evaluated,
    num_mcses,
    num_diagnoses,
    second_step,
    ss_cbmc_time,
    ss_cbmc_memory,
    ss_oracle_time,
    ss_oracle_memory,
    ss_cbmc_2nd_call_time,
    ss_cbmc_2nd_call_memory,
    ss_opt_cost,    
    ss_num_bugs,
    ss_num_diagnoses
)
VALUES'''

dataset_dir="/home/tcas"
data_dir="/home/results/tcas"
second_entry=0

methods_names=("CFaults" "CFaults-Refined" "BugAssist" "SNIPER")
methods=("CFaults" "CFaults-Refined" "BugAssist" "SNIPER")
