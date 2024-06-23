#!/usr/bin/env bash
#Title			: run_CFaults_on_benchmark.sh
#Usage			: bash run_CFaults_on_benchmark.sh -h
#Author			: pmorvalho
#Date			: October 02, 2023
#Description		: Runs CFaults' pipeline on an entire benchmark of instances.
#Notes			: 
# (C) Copyright 2023 Pedro Orvalho.
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
	    echo "$method_name: Dealing with $lab/$ex"
	    d=$inst_progs/$lab/$ex
	    # cp prints.* $d/.
	    num_unroll=$(cat $initial_dir/$tests_dir/$lab/$ex/$ex.unwind)
	    total=$((total+1))
	    mkdir -p $d
	    runsolver/src/runsolver -o $d/run.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT ./CFaults.sh -i $progs/$lab/$ex".c" -cp -e $lab/$ex -nu $num_unroll -o $d -v $ss_flags &
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
		echo "$method_name: Dealing with $year/$lab/$ex"
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
			runsolver/src/runsolver -o $d/$p/run.o -w $d/$p/watcher.w -v $d/$p/var.v -W $TIMEOUT --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./CFaults.sh -i $s -e $lab/$ex -nu $num_unroll -o $d/$p -v $INST_FLAGS $ss_flags &
		    else
			echo "Program: "$s
			runsolver/src/runsolver -o $d/$p/run.o -w $d/$p/watcher.w -v $d/$p/var.v -W $TIMEOUT --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./CFaults.sh -i $s -e $lab/$ex -nu $num_unroll -o $d/$p -v $INST_FLAGS $ss_flags
			break
		     fi
		done
		wait
	    done
	done
    done
}

process_TCAS_dataset(){
    num_unroll=3
    if [[ $REPR_SUBSET == 1 ]];
    then	
	v="v8"
	d=$inst_progs/$v
	v_dir=$progs/$v
	mkdir -p $d
	echo "$method_name: Dealing with version $v"
	runsolver/src/runsolver -o $d/run.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./CFaults.sh -i $v_dir/tcas.c -nu $num_unroll -t -o $d -v $ss_flags
	return
    fi
    for v_dir in $(find $progs/v* -mindepth 0 -maxdepth 0 -type d);
    do
	v=$(echo $v_dir | rev | cut -d '/' -f 1 | rev)
	d=$inst_progs/$v
	mkdir -p $d
	echo "$method_name: Dealing with version $v"
	runsolver/src/runsolver -o $d/run.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./CFaults.sh -i $v_dir/tcas.c -nu $num_unroll -t -o $d -v $ss_flags &
	total=$((total+1))
	# &
    done
    wait
}


process_ISCAS85(){
    for c_dir in $(find $progs/c* -mindepth 0 -maxdepth 0 -type d);
    do
	c=$(echo $c_dir | rev | cut -d '/' -f 1 | rev)
	for f in $(find $progs/$c/*.wcnf.gz -mindepth 0 -type f);
	do
	    f_name=$(echo $f | rev | cut -d '/' -f 1 | rev)
	    d=$inst_progs/$f_name
	    mkdir -p $d
	    echo "$method_name: Dealing with instance $f_name"
	    runsolver/src/runsolver -o $d/run.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT --vsize-limit $MEMOUT --rss-swap-limit $MEMOUT --timestamp ./CFaults.sh -i $f --iscas -o $d -v &
	    total=$((total+1))
	done       
	wait
   done
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
    echo "Tool: CFaults"
    if [[ $TCAS == 1 ]];
    then
	echo "Benchmark: TCAS"
    else
	if [[ $ISCAS == 1 ]];
	then
	    echo "Benchmark: ISCAS 85"
	else
	    echo "Benchmark: C-Pack-IPAs"
	fi
    fi
    echo "Enumerating All: $ENUM_ALL"    
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
ISCAS=0
CORRECT_PROG=0
SECOND_STEP=0
REPR_SUBSET=0
while [[ $# -gt 0 ]]
do
key="$1"
case $key in
    -c|--cpack_ipas)
	    CPACKIPAS=1
	    TCAS=0
	    ISCAS=0
	    shift
    ;;

    -cp|--correct_progs)
	    CORRECT_PROG=1
	    shift
    ;;
    -a|--enum_all)
	    ENUM_ALL="--enum_all"
	    shift
    ;;
    --iscas)
	    ISCAS=1
	    CPACKIPAS=0
	    TCAS=0
	    dataset_dir="iscas85-mobs"
	    shift
    ;;
    -rs|--repr_subset)
	    REPR_SUBSET=1
	    echo "Checking only a subset of the evaluation benchmark!"	
	    shift
    ;;
    -ss|--second_step)
	    SECOND_STEP=1
	    shift
    ;;
    -t|--tcas)
	    TCAS=1
	    CPACKIPAS=0
	    ISCAS=0
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
	echo "USAGE: $0 [-e|--enum_all] [-c|--cpack_ipas] [-t|--tcas] [--iscas] [-rs|--repr_subset] [-ss|--second_step] [-to|--timeout] [-h|--help]

    	Options:
	--> -c|--cpack_ipas -- to use C-Pack-IPAs dataset (Default).
	--> -t|--tcas -- to run CFaults on TCAS benchmark.
	--> --iscas -- To run CFaults on ICAS85 bechmark. In this benchmark, CFaults only runs the MaxSAT oracle on this benchmark.
	--> -cp|--correct_progs -- to run CFaults on correct programs. With this option, CFaults uses the entire test suite.	
	--> -a|--enum_all -- Enumerates all the WCNF solutions, even the ones with nonoptimum cost.
	--> -rs|--repr_subset -- Runs CFaults only on a representative subset of the chosen benchmark.
	--> -ss|--second_step -- Instrumentalizes the programs a second time introducing nondeterminism.
	--> -to|--timeout 3600s -- to specify the timeout for CBMC, RC2, in seconds. The default is 3600s.
	--> -h|--help -- to print this message"
	exit
    shift
    ;;
    *)
	echo "CFaults.sh: error: unrecognized arguments: $key"
	echo "Try [-h|--help] for help"
	shift
	exit
	;;    

esac
done

method_name="CFaults"
ss_flags=" -to "$TIMEOUT
if [[ $SECOND_STEP -eq 1 ]];
then
    method_name=$method_name"-Refined"
    ss_flags=$ss_flags" -ss "
fi

if [[ $CORRECT_PROG == 1 ]];
then
    echo "$method_name: Checking the reference implementations"
    progs=$dataset/"reference_implementations"
    inst_progs=$tmp_dir/"C-Pack-IPAs/reference_implementations/$method_name"
    process_reference_implementations
    echo
    echo

    echo "$method_name: Checking the correct programs"
    progs=$dataset/"correct_submissions"
    inst_progs=$tmp_dir/"C-Pack-IPAs/correct_submissions/$method_name"
    INST_FLAGS="-cp"
    process_C_Pack_IPAs_submissions
    echo
    echo
    
    summary
    echo "$method_name: Computations on the correct programs are over."
else
    if [[ $TCAS == 1 ]];
    then
	dataset_dir="tcas"
	initial_dir=$(pwd)
	echo "$method_name: Checking the TCAS dataset"	
	progs=$dataset_dir/"versions"
	inst_progs=$tmp_dir/"tcas/$method_name"
	process_TCAS_dataset
	summary
	echo "$method_name: Computations on the TCAS dataset are over."
    else
	if [[ $ISCAS == 1 ]];
	then
	    echo "$method_name: Running CFaults on ISCAS85"
	    progs=iscas85-mobs
	    inst_progs=$tmp_dir/"iscas85/$method_name"
	    process_ISCAS85
	    summary 
	    echo "$method_name: All instances from ISCAS 85 have been analyzed."
	else
	    echo "$method_name: Checking all incorrect submissions"
	    progs=$dataset/"semantically_incorrect_submissions"
	    inst_progs=$tmp_dir/"C-Pack-IPAs/incorrect_submissions/$method_name/"
	    INST_FLAGS=""
	    process_C_Pack_IPAs_submissions
	    summary
	    echo "$method_name: All incorrect programs have been analyzed!"
	fi
    fi
fi

rm -rf wdir_ex*
