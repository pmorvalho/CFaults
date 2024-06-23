# CFaults: Model-Based Diagnosis for Fault Localization in C with Multiple Test Cases

This is the implementation of _CFaults: Model-Based Diagnosis for Fault Localization in C with Multiple Test Cases_ [1] accepted at Formal Methods (FM) 2024.

CFaults introduces a novel formula-based fault localization technique for C programs capable of addressing any number of faults. Leveraging Model-Based Diagnosis (MBD) with multiple observations, CFaults consolidates all failing test cases into a unified MaxSAT formula, ensuring consistency in the fault localization process. In our paper, we show that CFaults only generates minimal diagnoses of faulty statements, while other formula-based fault localization methods tend to produce redundant diagnoses.

## LINK

GitHub URL: https://github.com/pmorvalho/CFaults/

Zenodo DOI: https://doi.org/10.5281/zenodo.12384842

## REQUIREMENTS

All requirements are installed in the Docker image available on Zenodo. Nevertheless, the script `config.sh` executes the commands to install all requirements.

```
bash config.sh
```

## EXPERIMENT SETUP

All of the experiments were conducted on an `Intel(R) Xeon(R) Silver computer with 4210R CPUs @ 2.40GHz` running Linux Debian 10.2.

### EXPERIMENTS

Requirements:
- RAM: 64 GB
- Time Limit: 3600s
- CPUs: at least 40
- Total time: ~45 hours

CFaults has been evaluated using two benchmarks of C programs: _TCAS_ [2] and _C-Pack-IPAs_ [3]:

- TCAS includes a C program from Siemens and 41 versions with intentionally introduced faults, with known positions and types.

- C-Pack-IPAs is a set of student programs collected during an introductory programming course for ten assignments over three distinct academic years, comprising 486 faulty programs and 799 correct implementations.


In our paper's evaluation, we evaluate 4 different _formula-based fault localization (FBFL)_ approaches: _BugAssist_ [4], _SNIPER_ [5], and CFaults with and without calling the refinement step. Furthermore, since the source code of BugAssist and SNIPER is either unavailable or no longer maintained (resulting in compilation and linking issues), prototypes of their algorithms were implemented. It is worth noting that the original version of SNIPER could only analyze programs that utilized a subset of ANSI-C, lacked support for loops and recursion, and could only partially handle global variables, arrays, and pointers. In this work, both SNIPER and BugAssist handle ANSI-C programs, as their algorithms are built on top of CFaults's unroller and instrumentalizer modules.

So we run each FBFL approach on 41 faulty programs from TCAS and 486 programs from C-Pack-IPAs.

Number of runs:

- TCAS (41 programs):
  - Each program is analyzed 4 times, one for each FBFL approach (164 runs).

- C-Pack-IPs (486 programs):
  - Each program is analyzed 4 times, one for each FBFL approach (1944 runs).
  - This benchmark contains 10 programming exercises from 3 academic years (30 subsets of programs). We call the FBFL tools in parallel 30 times, once for all the programs in a given programming exercise (10 exercises) from a given academic year (3 years).

In our experiments, **using a time limit of 3600s, took us ~45 hours to compute everything**, calling each programming exercise of C-Pack-IPAs in parallel and using 40 CPUs.

### SUBSET OF EXPERIMENTS

We propose to evaluate our artifact on a **representative subset** of each benchmarks that contains around 6% of the total number of programs. This representative subset is composed by 1 program from TCAS, and 30 programs from C-Pack-IPAs (one from each exercise (10) from each academic year (3)). Moreover, we propose a time limit of 60s for this evaluation.

**__Note for Reviewers:__** We used a maximum of 40 CPUs simultaneously. To reproduce the full set of experiments presented in our paper, a machine with at least 40 CPUs and 64 GB of RAM should be used. However, to reproduce the experiments using the suggested representative subset of programs, a machine with just 1 CPU can be used.

Requirements for our representative subset of programs:
- RAM: at least 32 GB
- Time Limit: 60s
- CPUs: at least 1
- Total time: ~1 hour

## REPRODUCIBILITY INSTRUCTIONS

The artifact is in the directory `/home/` of the docker image.

All the following commands must be run from the home directory unless stated otherwise.

### OPTION #1

To run the motivating example from our paper:
(Each FBFL tool should take less than one minute to process the motivating example)

#### CFaults
```
./CFaults.sh -i examples/fm2024_example.c -o motivating_example_CFaults -nu 3 -e lab02/ex01 -v
```

#### CFaults-Refined
```
./CFaults.sh -i examples/fm2024_example.c -o motivating_example_CFaults-Refined -nu 3 -e lab02/ex01 -ss -v
```

#### BugAssist
```
./BugAssist.sh -i examples/fm2024_example.c -o motivating_example_BugAssist -nu 3 -e lab02/ex01 -v
```

#### SNIPER
```
./SNIPER.sh -i examples/fm2024_example.c -o motivating_example_SNIPER -nu 3 -e lab02/ex01 -v
```

### OPTION #2 (OUR RECOMMENDATION) 

To run all FBFL approaches on the representative subset of our dataset 6%: 
(This should take around 50 minutes to process using our docker image)

```
bash run_subset.sh 
```

### OPTION #3

To run all FBFL approaches on the representative subset of our dataset 6% with a time limit of 180s (3 min): 
(This should take at most 2 hours to process using our docker image)

```
bash run_subset.sh 180
```

### OPTION #4

This corresponds to our paper's evaluation. To run all FBFL approaches on the entire benchmarks of programs (TCAS and C-Pack-IPAs), and reproduce the results section in the paper, use the script run_all.sh: (takes around 45 hours)

```
bash run_all.sh
```

************************** 

## RESULTS

All logs are stored in `/home/results/`

Both scripts `run_subset.sh` and `run_all.sh` after executing all FBFL tools, generate a sqlite3 database, csvs files and a set of plots based on the gathered results.

More specifically, these scripts call the following script:
```
cd database	
./gen_database.sh
cd ..
```

This script generates the sqlite3 database, and calls the `data_2_plots.py` script that generates the csv files and plots.

### TABLE 3 (Section 5)

The script `get_fault_loc_results.py` generates Table 3 presented in Section 5 of our paper [1]. This can be done by running:

```
cd database
python3 get_fault_loc_results.py
cd ..
```

Note: This script needs to be called after `gen_database.sh`


### PLOTS (Section 5)

The script `data_2_plots.py` generates the csv files and plots presented in Section 5 of our paper [1].

```
cd database
python3 data_2_plots.py
cd ..
```

Note: This script needs to be called after `gen_database.sh`

Cactus plots:
 - Fig.2 (a) - Time Performance on TCAS 
 
   	 CSV file:  `results/csvs/tcas-cactus-time.pdf`
	 
	 plot (pdf): `results/plots/tcas-cactus-time.pdf`	 

 - Fig.2 (b) - Time Performance on C-Pack-IPAs
 
   	 CSV file:  `results/csvs/CPackIPAs-cactus-time.pdf`
	 
	 plot (pdf): `results/plots/CPackIPAs-cactus-time.pdf`

Scatter plots:
 - Fig.2 (c) - Costs of refined diagnoses on C-Pack-IPAs
 
   	 CSV file:  `results/csvs/CPackIPAs-scatter-opt_cost-CFaults-CFaults-Refined.csv`
	 
	 plot (pdf): `results/plots/CPackIPAs-scatter-opt_cost-CFaults-CFaults-Refined.pdf`

 - Fig.2 (d) - Costs of diagnoses on C-Pack-IPAs
 
   	 CSV file:  `results/csvs/CPackIPAs-scatter-opt_cost-BugAssist-CFaults.csv`
	 
	 plot (pdf): `results/plots/CPackIPAs-scatter-opt_cost-BugAssist-CFaults.pdf`

 - Fig.2 (e) - #Diagnoses generated on C-Pack-IPAs
 
   	 CSV file:  `results/csvs/CPackIPAs-scatter-num_diagnoses-CFaults-SNIPER.csv`
	 
	 plot (pdf): `results/plots/CPackIPAs-scatter-num_diagnoses-CFaults-SNIPER.pdf`


## ORIGINAL RESULTS

The artifact also includes the results from the run, which are shown in the paper and stored in the SQLite database: `database/fm2024-results.db`. This database is built from our logs. Since it is unlikely that the reviewers will have time to reproduce all the results due to the extensive CPU computation hours required, making the original results available will help clarify any questions the reviewers may have.

These results were obtained using the machine described in the _EXPERIMENT RUNTIME_ section. Since running the FBFL tools in Docker is slower than on our servers, there may be some differences between running all the experiments in Docker compared to our machine. However, the same trends in the results should be observed in Docker.

To compute our CSVs and plots, run the following commands:

```
cd database
cp fm2024-results.db results.db
python3 data_2_plots.py
```

Afterwards, our paper's plots and respective CSV files can be found in `database/plots/` and `database/csvs/`, respectively.

## SCRIPTS

All the following scripts can be run with the -h flag to display a help message.

- `CFaults.sh`

  This script runs CFaults' pipeline on a program/wcnf formula from C-Pack-IPAs, or TCAS.
  The logs generated by this script are stored in: `results/BENCHMARK/CFaults`.

- `BugAssist.sh`

  This script runs BugAssist's pipeline on a program/wcnf formula from C-Pack-IPAs, or TCAS.
  The logs generated by this script are stored in: `results/BENCHMARK/BugAssist`.

- `SNIPER.sh`

  This script runs SNIPER's pipeline on a program/wcnf formula from C-Pack-IPAs, or TCAS.
  The logs generated by this script are stored in: `results/BENCHMARK/SNIPER`.

- `run_CFaults_on_benchmark.sh`, `run_BugAssist_on_benchmark.sh` and `run_SNIPER_on_benchmark.sh`

   These scripts run the respective FBFL tool's pipeline on an entire benchmark of programs i.e., C-Pack-IPAs or TCAS.

- `cnf_2_relaxed_wcnf.py`

   Given a CNF formula generated by CBMC, this script generates a WCNF. The soft clauses are the relaxation variables (bool) of the program that indicate if a given line is executed or not.

- `program_unroller.py`

   Unrolls a program using a different iteration for each IO test. Injects assertions into the end of each test scope. 

- `program_instrumentalizer.py`

   Instrumentalizes each program instruction or expression.

- `oracle.py`

   Oracle. RC2 Solver, returns which lines should be removed.

- `database/get_sqlite3_table.sh`

  Prints a SQLite3 table for fault localization results either using TCAS or CPackIPAs datasets.
  
## AVAILABILITY

The source code for CFaults is also publicly available at https://github.com/pmorvalho/CFaults

This repository should not be used to reproduce the artifact, but it contains the current version of the tool and will continue to be developed and shared with the research community.

## REFERENCES

[1] P. Orvalho, M. Janota, and V. Manquinho. CFaults: Model-Based Diagnosis for Fault Localization in C with Multiple Test Cases. The 26th International Symposium on Formal Methods, FM 2024.

[2] Do, H., Elbaum, S.G., Rothermel, G.: Supporting controlled experimentation with testing techniques: An infrastructure and its potential impact. Empir. Softw. Eng. (2005).

[3] P. Orvalho, M. Janota, and V. Manquinho. C-Pack of IPAs: A C90 Program Benchmark of Introductory Programming Assignments. In the 5th International Workshop on Automated Program Repair, APR 2024, co-located with ICSE 2024.

[4] Jose, M., Majumdar, R.: Cause clue clauses: error localization using maximum satisfiability. In: Proceedings of the 32nd ACM SIGPLAN Conference on Programming Language Design and Implementation, PLDI 2011.

[5] Lamraoui, S., Nakajima, S.: A formula-based approach for automatic fault localization of multi-fault programs. J. Inf. Process. 24(1), 88–98 (2016).
