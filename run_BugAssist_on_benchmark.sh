#!/usr/bin/env bash
#Title			: run_BugAssist_on_benchmark.sh
#Usage			: bash run_BugAssist_on_benchmark.sh -h
#Author			: pmorvalho
#Date			: January 28, 2024
#Description		: Runs BugAssist on an entire benchmark of instances.
#Notes			: 
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

dataset="C-Pack-IPAs"
dataset_dir="C-Pack-IPAs"
labs=("lab02")
years=("year-1" "year-2" "year-3")
tests_dir="tests_updated"
TIMEOUT=3600s
MEMOUT=32000
PErros=0
IOErrors=0
total=0
ftype="wcnf"
tmp_dir="results"

process_reference_implementations(){
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex_dir in $(find $tests_dir/$lab/ex* -mindepth 0 -maxdepth 0 -type d);
	do
	    ex=$(echo $ex_dir | rev | cut -d '/' -f 1 | rev)
	    echo "BugAssist: Dealing with $lab/$ex"
	    d=$inst_progs/$lab/$ex
	    # cp prints.* $d/.
	    num_unroll=$(cat $initial_dir/$tests_dir/$lab/$ex/$ex.unwind)
	    total=$((total+1))
	    mkdir -p $d
	    runsolver/src/runsolver -o $d/run.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./BugAssist.sh -i $progs/$lab/$ex".c" -cp -e $lab/$ex -nu $num_unroll -o $d -to $TIMEOUT -v &
	done
	wait
    done
}

process_C_Pack_IPAs_submissions(){
    for((y=0;y<${#years[@]};y++));
    do
	year=${years[$y]}
	for((l=0;l<${#labs[@]};l++));
	do
	    lab=${labs[$l]}
	    for ex_dir in $(find $progs/$year/$lab/ex* -mindepth 0 -maxdepth 0 -type d);
	    do
		ex=$(echo $ex_dir | rev | cut -d '/' -f 1 | rev)
		echo "BugAssist: Dealing with $year/$lab/$ex"
		d=$inst_progs/$year/$lab/$ex
		# cp prints.* $d/.
		num_unroll=$(cat $initial_dir/$tests_dir/$lab/$ex/$ex.unwind)	   
		for s in $(find $progs/$year/$lab/$ex/*".c" -mindepth 0 -maxdepth 0 -type f);
		do
		    p=$(echo $s | rev | cut -d '/' -f 1 | rev | sed "s/\.c//g")	       
		    total=$((total+1))
		    mkdir -p $d/$p
		    if [[ $REPR_SUBSET == 0 ]];
		    then
			runsolver/src/runsolver -o $d/$p/run.o -w $d/$p/watcher.w -v $d/$p/var.v -W $TIMEOUT  --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./BugAssist.sh -i $s -e $lab/$ex -nu $num_unroll -o $d/$p -v $INST_FLAGS -to $TIMEOUT &
		    else
			echo "Program: "$s
			runsolver/src/runsolver -o $d/$p/run.o -w $d/$p/watcher.w -v $d/$p/var.v -W $TIMEOUT  --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./BugAssist.sh -i $s -e $lab/$ex -nu $num_unroll -o $d/$p -v $INST_FLAGS -to $TIMEOUT
			break
		    fi
		done
		wait
	    done
	done
    done
}

process_TCAS_dataset(){
    echo "Dealing with source tcas.c"
    num_unroll=3
    if [[ $REPR_SUBSET == 1 ]];
    then	
	v="v8"
	d=$inst_progs/$v
	v_dir=$progs/$v
	mkdir -p $d
	echo "CFaults: Dealing with version $v"
	runsolver/src/runsolver -o $d/run.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT  --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./BugAssist.sh -i $v_dir/tcas.c -nu $num_unroll -t -o $d -v -to $TIMEOUT
	return
    fi

    for v_dir in $(find $progs/v* -mindepth 0 -maxdepth 0 -type d);
    do
	v=$(echo $v_dir | rev | cut -d '/' -f 1 | rev)
	d=$inst_progs/$v
	mkdir -p $d
	echo "BugAssist: Dealing with version $v"
	runsolver/src/runsolver -o $d/run.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT  --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./BugAssist.sh -i $v_dir/tcas.c -nu $num_unroll -t -o $d -v -to $TIMEOUT &
	total=$((total+1))
    done
    wait
}

summary(){
    TOs_cbmc=$(grep -l "Timeout running CBMC" `find $inst_progs/ -type f -name run.o` | wc -l)
    TOs_rc2=$(grep -l "Timeout solving $ftype" `find $inst_progs/ -type f -name run.o` | wc -l)
    UNSATs=$(grep -l "UNSAT" `find $inst_progs/ -type f -name run.o` | wc -l)
    IOErrors=$(grep -l "CORRECT .*printf" `find $inst_progs/ -type f -name run.o` | wc -l)
    PErrors=$(grep -l "Presentation" `find $inst_progs/ -type f -name run.o` | wc -l)
    CompErrors=$(grep -l "Compilation Time Error" `find $inst_progs/ -type f -name run.o` | wc -l)
    InstErrors=$(grep -l "Error instrumentalizing" `find $inst_progs/ -type f -name run.o` | wc -l)
    uninitVars=$(grep -l "Uninitialized var" `find $inst_progs/ -type f -name run.o` | wc -l)
    divZero=$(grep -l "Divison By Zero" `find $inst_progs/ -type f -name run.o` | wc -l)
    Warns=$(grep -l "Warning" `find $inst_progs/ -type f -name run.o` | wc -l)
    ZCost=$(grep -l " 0 faults" `find $inst_progs/ -type f -name run.o` | wc -l)
    NZCost=$(grep " [1-9][0-9]* fault(s)" `find $inst_progs/ -type f -name run.o` | grep "[1-9][0-9]*" | wc -l)
    ScanfOOB=$(grep -l "Scanf is accessing out-of-bound memory!"  `find $inst_progs/ -type f -name run.o` | wc -l)
    ArrayOOB=$(grep -l "Some array is accessing out-of-bound memory!" `find $inst_progs/ -type f -name run.o` | wc -l)
    fault_loc_succ=$(grep -l "SUCCESS"  `find $inst_progs/ -type f -name run.o` | wc -l)
    fault_loc_failed=$(grep -l "FAILED" `find $inst_progs/ -type f -name run.o` | wc -l)
    fault_loc_memout=$(grep -l "MEMOUT=t" `find $inst_progs/ -type f -maxdepth 5 -name var.v` | wc -l)
    fault_loc_timeout=$(grep -l "TIMEOUT=t" `find $inst_progs/ -type f -maxdepth 5 -name var.v` | wc -l)    

    
    echo "---- Summary ----"
    echo "Tool: BugAssist"
    if [[ $TCAS == 0 ]];
    then
       echo "Benchmark: C-Pack-IPAs"
    else
       echo "Benchmark: TCAS"
    fi
    echo "#CBMC (Timeouts): $TOs_cbmc"
    echo "#Out-of-bounds memory accesses: $ScanfOOB (Scanfs) and $ArrayOOB (Other arrays)"
    echo "#RC2 (UNSATs): $UNSATs (UNSAT) and $TOs_rc2 (TIMEOUTs)"
    echo "#Input-Output Errors  Ignored: $PErrors (Presentation Errors) and $IOErrors (Printf/Scanf's format)"
    echo "#Compilation Errors: $CompErrors"
    echo "#Errors while instrumentalizing: $InstErrors"
    echo "#Uninitialized Variables: $uninitVars"
    echo "#Warnings: $Warns (#Divisions by Zero: $divZero)"
    echo "#Programs with 0 faults: $ZCost"
    echo "#Programs with faults: $NZCost"
    echo "Fault Localization"
    echo "  - Success: $fault_loc_succ"
    echo "  - Failed: $fault_loc_failed"     
    echo "  - MEMOUTs: $fault_loc_memout"
    echo "  - TIMEOUTs: $fault_loc_timeout"        
    echo "Total number of programs evaluated: $total ($((TOs_cbmc+ScanfOOB+ArrayOOB+TOs_rc2+UNSATs+IOErrors+PErrors+CompErrors+InstErrors+uninitVars+Warns+ZCost+NZCost)))"
    echo
    echo
}

initial_dir=$(pwd)
CPACKIPAS=1
TCAS=0
CORRECT_PROG=0
REPR_SUBSET=0
while [[ $# -gt 0 ]]
do
key="$1"
case $key in
    -c|--cpack_ipas)
	    CPACKIPAS=1
	    TCAS=0
	    shift
    ;;

    -cp|--correct_progs)
	    CORRECT_PROG=1
	    shift
    ;;
    -rs|--repr_subset)
	    echo "Checking only a subset of the evaluation benchmark!"
	    REPR_SUBSET=1
	    shift
    ;;   
    -t|--tcas)
	    TCAS=1
	    CPACKIPAS=0
	    dataset_dir="tcas"
	    traces_dir=$dataset_dir/"traces"
	    shift
    ;;
    -to|--timeout)
	    TIMEOUT=$2
	    shift
	    shift
    ;;    
    -v|--verbose)
	    VERBOSE=1
	    shift
    ;;    
    -h|--help)
	echo "USAGE: $0 [-e|--enum_all] [-c|--cpack_ipas]  [-rs|--repr_subset] [-t|--tcas]  [-to|--timeout] [-h|--help]

    	Options:
	--> -c|--cpack_ipas -- to use C-Pack-IPAs dataset (Default).
	--> -t|--tcas -- to run BugAssist on TCAS benchmark.
	--> -cp|--correct_progs -- to run BugAssist on correct programs. With this option, BugAssist uses the entire test suite.	
	--> -rs|--repr_subset -- Runs CFaults only on a representative subset of the chosen benchmark.
	--> -to|--timeout 3600s -- to specify the timeout for CBMC, RC2, in seconds. The default is 3600s.
	--> -h|--help -- to print this message"
	exit
    shift
    ;;
    *)
	echo "BugAssist.sh: error: unrecognized arguments: $key"
	echo "Try [-h|--help] for help"
	shift
	exit
	;;    

esac
done


if [[ $CORRECT_PROG == 1 ]];
then
    echo "BugAssist: Checking the reference implementations"
    progs=$dataset/"reference_implementations"
    inst_progs=$tmp_dir/"C-Pack-IPAs/reference_implementations/BugAssist"
    process_reference_implementations
    echo
    echo

    echo "BugAssist: Checking the correct programs"
    progs=$dataset/"correct_submissions"
    inst_progs=$tmp_dir/"C-Pack-IPAs/correct_submissions/BugAssist"
    INST_FLAGS="-cp"
    process_C_Pack_IPAs_submissions
    echo
    echo
    
    summary
    echo "BugAssist: Computations on the correct programs are over."
else
    if [[ $TCAS == 1 ]];
    then
	dataset_dir="tcas"
	initial_dir=$(pwd)
	echo "BugAssist: Checking the TCAS dataset"	
	progs=$dataset_dir/"versions"
	inst_progs=$tmp_dir/"tcas/BugAssist"
	process_TCAS_dataset
	summary 
	echo "BugAssist: Computations on the TCAS dataset are over."
    else
	echo "BugAssist: Checking all incorrect submissions"
	progs=$dataset/"semantically_incorrect_submissions"
	inst_progs=$tmp_dir/"C-Pack-IPAs/incorrect_submissions/BugAssist"
	INST_FLAGS=""
	process_C_Pack_IPAs_submissions
	summary 
	echo "BugAssist: All incorrect programs have been analyzed!"
    fi
fi

rm -rf wdir_ex*
