#!/usr/bin/env bash
#Title			: CFaults.sh 
#Usage			: bash CFaults.sh -h
#Author			: pmorvalho
#Date			: January 26, 2024
#Description		: Runs CFaults' pipeline on a program/wcnf formula from C-Pack-IPAs, TCAS or ICAS85
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
ftype="wcnf"
tmp_dir="results"
CPACKIPAS=1
TCAS=0
ISCAS=0

sanity_check(){
    if [[ $VERBOSE ]];
    then
	echo "Starting sanity check"
    fi
    mkdir -p $d/faults
    cp prints.* $d/faults/.
    for ((faults_index=0; ; faults_index++));
    do
	if [[ $VERBOSE ]];
	then
	    echo "Faults index: $faults_index"
	fi
	new_p=$d/"faults"/$p"_faults-$faults_index.c"
	stmts_map=$d/"faults/$faults_index.pkl.gz"
	# if [[ $TCAS == 1 ]];
	# then
	python3 program_instrumentalizer.py -ip $prog -o $new_p $tests_2_use -msi $stmts_map -nu $NUM_UNROLL -ssv $faults_dict -fi $faults_index >& $d/"faults"/$p.pi-$faults_index-out
	# else	       
	#     python3 program_instrumentalizer.py -ip $prog -o $new_p -upt -e $IPA -hw -msi $stmts_map -nu $NUM_UNROLL -ssv $faults_dict -fi $faults_index >& $d/"faults"/$p.pi-$faults_index-out
	# fi
	if [[ ! ($? -eq 0) && $(grep "No more faults to relax!" $d/"faults"/$p.pi-$faults_index-out) != "" ]];
        then
	    echo "Could not find any faulty statements!"
	    if [[ $VERBOSE ]];
	    then
		echo "#Attempts: $faults_index"
		if [[ $CORRECT_PROG == 1 && $faults_index -eq 0 ]];
		then
		    echo "After checking $faults_index possible sets of faults."
		    echo "SUCCESS"
		    exit
		fi
		echo "FAILED"
	    fi
	    echo
	    return;
        fi
        aux_dir=$d"/faults/cbmc-$faults_index"
	mkdir -p $aux_dir
	runsolver/src/runsolver -o $aux_dir/out.o -w $aux_dir/watcher.w -v $aux_dir/var.v -W $TIMEOUT --rss-swap-limit $MEMOUT \
				      cbmc/src/cbmc/cbmc $new_p prints.c --unwind $NUM_UNROLL --16 
	if [[ $(grep "FAILURE" $aux_dir/out.o) == "" ]];
        then
	    continue;
	fi
	if [[ $VERBOSE ]];
	then
	    flag_verb=" -v "
	    echo "After checking $faults_index possible sets of faults."
	    echo "#Attempts: $faults_index"
	fi
	python3 get_faulty_statements.py -d $faults_dict -fi $faults_index -id $p $flag_verb | tee -a $output_dir/$p.fdbk
	if [[ $VERBOSE ]];
	then
	    echo "SUCCESS"
	fi	
	exit
    done
    echo
}

CBMC_bounds_check(){
    # $1 program on which we are going to run CBMC
    # $2 dir
    # $3 filename

    aux_dir=$2"/cbmc-2nd"
    if [[ ! -d $aux_dir ]];
    then
       mkdir -p $aux_dir
    fi
    runsolver/src/runsolver -o $aux_dir/out.o -w $aux_dir/watcher.w -v $aux_dir/var.v -W $TIMEOUT --rss-swap-limit $MEMOUT \
 				  timeout $TIMEOUT cbmc/src/cbmc/cbmc $1 --16 --unwind $NUM_UNROLL --bounds-check
    if [[ $(grep "TIMEOUT=t" $aux_dir"/var.v" ) ]]; then
	echo "Timeout running CBMC on $1 (Checking Memory Accesses)" | tee -a $3.fdbk
	exit
    fi
    out_of_bounds=$(grep -r ".*array_bounds.* FAILURE" $aux_dir"/out.o" | grep -v "output")
    if [[ $out_of_bounds ]];
    then 
	if [[ $(echo $out_of_bounds | grep  "__input") ]];
	then
	    echo "$2: Scanf is accessing out-of-bound memory!" | tee -a $3.fdbk
	else
	    echo "$2: Some array is accessing out-of-bound memory!"	 | tee -a $3.fdbk
	fi
	exit
    fi    
}

Oracle(){
    # $1 filename
    # $2 mapping from instumentalized instructions to the students' instructions (pickle gzip)
    # $3 dir
    
    aux_dir=$3"/oracle"
    if [[ ! -d $aux_dir ]];
    then
       mkdir -p $aux_dir
    fi
    runsolver/src/runsolver -o $aux_dir/out.o -w $aux_dir/watcher.w -v $aux_dir/var.v -W $TIMEOUT --rss-swap-limit $MEMOUT python3 oracle.py --$ftype $1"."$ftype -msi $2 --faults_dict $3/localized_faults.pkl.gz $ENUM_ALL
    if [[ $? = 0 ]]; then
	if [[ $(grep "TIMEOUT=t" $aux_dir/var.v) ]]; then	
	    gzip -f $1"."$ftype	
	    echo "Timeout solving $ftype formulae $1."$ftype
	    echo "Timeout running RC2" > $1.fdbk
	    exit
	fi
    else
	echo "Error while running RC2 on formulae $1."$ftype
	echo "Error while running RC2" > $1.fdbk
	exit
    fi
    gzip -f $1"."$ftype &
    if [[ $(grep "UNSAT" $aux_dir"/out.o") ]]; then
	echo "UNSAT formulae $1."$ftype
	echo "UNSAT WCNF formula" > $1.fdbk
	exit
    else
	cost=$(cat $aux_dir"/out.o" | grep -oh "\#Bugs: [0-9]*" | head -1 | grep -oh "[0-9]*" )
	echo $cost	
   fi
}


cnf_2_wcnf_translation(){
    # $1 CNF filename
    # $2 mapping from instumentalized instructions to the students' instructions (pickle gzip)
    
    if [[ $ftype == "pwcnf" ]];
    then
	python3 cnf_2_relaxed_wcnf.py -i $1".cnf" -p  -o $1"."$ftype -msi $2 -nu $NUM_UNROLL
    else
	python3 cnf_2_relaxed_wcnf.py -i $1".cnf" -o $1"."$ftype -msi $2 -nu $NUM_UNROLL
    fi
    gzip -f $1".cnf" &
}


CBMC(){
    # $1 program on which we are going to run CBMC
    # $2 output filename
    # $3 dir

    aux_dir=$3"/cbmc"
    if [[ ! -d $aux_dir ]];
    then
       mkdir -p $aux_dir
    fi
    runsolver/src/runsolver -o $aux_dir/out.o -w $aux_dir/watcher.w -v $aux_dir/var.v -W $TIMEOUT --rss-swap-limit $MEMOUT \
    cbmc/src/cbmc/cbmc $1 prints.c --dimacs --16 --unwind $NUM_UNROLL --outfile $2".cnf"
    if [[ $(grep "TIMEOUT=t" $aux_dir/var.v) ]]; then
	echo "Timeout running CBMC on $1"
	echo "Timeout running CBMC" > $2.fdbk
	exit
    fi
}


instrumentalization_step(){
    # instrumentalization step, and this functions also checks which tests are failing in the test suite and next unrolls and instrumentalizes the program
    p=$1
    d=$2
    new_p=$3
    stmts_map=$4
    if [[ $5 != "" ]];
    then
	ss_vars="-ssv "$5
    fi
    tests_2_use=""
    if [[ -f $d/$p.fdbk ]];
    then	
	rm $d/$p.fdbk
    fi
    if [[ $CORRECT_PROG == 1 ]];
    then
	tests_2_use=" -upt -hw "
	if [[ $TCAS == 1 ]];
	then
	    tests_2_use=$tests_2_use" --test_dir $dataset_dir --traces_dir $traces_dir/$p "
	else
	    tests_2_use="-e $IPA "$tests_2_use
	fi
    else
	if [[ $TCAS == 1 ]];
	then
	    tests_2_use="--test_dir $dataset_dir --traces_dir $traces_dir/$p -hw "
	else
	    init_check=$(bash check_unrolled_tests.sh $prog $dataset_dir/tests/$IPA 2> err.txt | grep -v "timeout" )
            if [[ -f err.txt ]];
            then
                rm err.txt
            fi

	    if echo $init_check | grep -v -q "\[" ;
	    then
		echo "FIXED $d/$p: "$init_check | tee $d/$p.fdbk
		echo
		echo "SUCCESS"
		echo 
		exit
	    fi
	    tests_2_use="-e $IPA -t "$init_check" -hw"
	fi
    fi
    python3 program_instrumentalizer.py -ip $prog -o $new_p $tests_2_use -msi $stmts_map -nu $NUM_UNROLL $ss_vars >& $d/$p.pi-out
    if [[ $? = 0 ]]; then
	gcc $d/prints.c $d/nondet_vals.c $new_p -o $d/$p.gcc-out >& $d/$p.pi-gcc
	if [[ $? = 0 ]]; then
	    # Next CFaults will call CBMC
	    return
	else
	    echo "ERROR"
	    echo "Error compiling $new_p" | tee -a $d/$p.fdbk
	    exit
	fi
	rm $d/$p.gcc-out
    else
	if [[ $(grep "This program is correct according to the given set of IO tests." $d/$p.pi-out) != ""  ]];
	then
	    echo "FIXED $d/$p after unrolling"
	    exit
	else
	    if [[ $(grep "Warning" $d/$p.pi-out) ]];
	    then
		echo "FIXED: $new_p "$(grep "Warning" $d/$p.pi-out)
		echo $(grep "Warning" $d/$p.pi-out) > $d/$p.fdbk
		echo
		echo "SUCCESS"
		echo
		exit
	    else
		echo "ERROR"
		echo "Error instrumentalizing $new_p" | tee -a $d/$p.fdbk
		exit
	    fi
	fi
    fi
}


CFaults_pipeline(){
    if [[ $VERBOSE ]];
    then
	echo "Fault Localization Method: CFaults"
    fi
    ss_vars=$1 # only used if this function is called a second time
    if [[ $TCAS == 0 ]];
    then
	p=$(echo $prog | rev | cut -d '/' -f 1 | rev | sed "s/\.c//g")
    else
	if [[ $VERBOSE ]];
	then
	    echo "Using TCAS benchmark"
	fi
	p=$(echo $prog | rev | cut -d '/' -f 2 | rev )
    fi
    d=$output_dir
    if [[ ! -d $d ]];
    then
	mkdir -p $d
    fi
    if [[ $ss_vars == 1 ]];
    then
	ss_vars=$d"/localized_faults.pkl.gz"
	d=$d"/ss-instrumentalization"
	mkdir -p $d
    fi
    new_p=$d/$p"_instrumentalized.c"    
    stmts_map=$d/$p".pkl.gz"
    faults_dict=$d"/localized_faults.pkl.gz"
    cp prints* $d/.
    cp nondet_vals.c $d/.    
    if [[ $VERBOSE ]];
    then
	echo "Instrumentalizing $p"
    fi
    instrumentalization_step $p $d $new_p $stmts_map $ss_vars
    if [[ $VERBOSE ]];
    then
	echo "Calling CBMC on $p"
    fi
    CBMC $new_p $d/$p $d
    if [[ $VERBOSE ]];
    then
	echo "Translating the CNF into a WCNF"
    fi    
    cnf_2_wcnf_translation $d/$p $stmts_map
    if [[ $VERBOSE ]];
    then
	echo "Calling the MaxSAT Oracle on $p"
    fi         
    cost=$(Oracle $d/$p $stmts_map $d)
    if [[ $(echo $cost | grep "UNSAT") != ""  ]];
    then
	echo "UNSAT $p" | tee -a $d/$p.fdbk
	if [[ $ss_vars == "" ]]; 
	then
	    exit
	else
	    d=$output_dir
	    cost=$(cat $d/oracle/out.o | grep -oh "\#Bugs: [0-9]*" | grep -oh "[0-9]*" | sort | head -n 1)
	    if [[ $cost == "" ]];
	    then
		cost="0"
	    fi
        fi
    fi
    if [[ $VERBOSE && $SECOND_STEP ]];
    then
	echo "Got an initial cost of $cost"
	echo
    fi
    wait
    if [[ $VERBOSE ]];
    then
	echo $(grep "Diagnoses=" $d/oracle/out.o)
    fi    
    if [[ $cost == "0" && $CORRECT_PROG == "" ]];
    then
	CBMC_bounds_check $new_p $d $d/$p
    else
	if [[ $cost == "UNSAT" ]];
	then
	    echo "UNSAT"
	    exit 0
	fi
	cost=$((cost))
	if [[ $cost -gt 1 && $SECOND_STEP == 1 ]];
	then
	    # Call second instrumentalization step
	    if [[ $VERBOSE ]];
	    then
		echo "Executing a second instrumentalization on $p"
	    fi
	    SECOND_STEP=0
	    CFaults_pipeline 1
	    return
	else
	    # sanity check
	    sanity_check 	    
	    echo
	    echo
	    return;
	fi
    fi	
}

CFaults_pipeline_4_ISCAS(){
    i=$(echo $prog | rev | cut -d '/' -f 1 | rev | sed "s/\.wcnf\.gz//g")
    p=$(echo $prog | sed "s/\.gz//g")
    gunzip -k $prog
    mkdir -p $output_dir
    if [[ $VERBOSE ]];
    then
	echo "Unrolling ISCAS wcnf: $i"
    fi  
    python3 iscas85/unroll_wcnfs_based_on_observations.py -i $p -o $output_dir/$i"-unrolled.wcnf"
    if [[ $VERBOSE ]];
    then
	echo "Gathering all MaxSAT solutions for $i"
	echo
    fi
    aux_dir=$output_dir"/oracle"
    mkdir -p $aux_dir
    runsolver/src/runsolver -o $aux_dir/out.o -w $aux_dir/watcher.w -v $aux_dir/var.v -W $TIMEOUT --rss-swap-limit $MEMOUT python3 oracle.py --wcnf $output_dir/$i"-unrolled.wcnf" --faults_dict $output_dir/localized_faults.pkl.gz   
    gzip -f $output_dir/$i"-unrolled.wcnf" &
    rm $p
    cost=$(cat $aux_dir/out.o | grep "o [0-9]*$" | head -1 | grep -oh "[0-9]*")
    echo
    echo
    echo "Successfully localized $cost faults in $i." | tee -a $output_dir/$i.fdbk
    echo | tee -a $output_dir/$i.fdbk
    echo "Consider the following circuit component(s) that should be carefully analyzed.:"  | tee -a $output_dir/$i.fdbk
    cat $aux_dir"/out.o" | grep "C_" | awk '{print $0 "\n OR"}' | head -n -1 | tee -a $output_dir/$i.fdbk
    echo
    echo
}

tests_2_use=""
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
    -i|--input)
	    prog=$2
	    shift
	    shift
    ;;
    -e|--ipa)
	    IPA=$2
	    shift
	    shift
    ;;
    --iscas)
	    ISCAS=1
	    CPACKIPAS=0
	    TCAS=0
	    dataset_dir="iscas85-mobs"
	    shift
    ;;    
    -nu|--num_unroll)
	    NUM_UNROLL=$2
	    shift
	    shift
    ;;            
    -o|--output_dir)
	    output_dir=$2
	    shift
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
    -td|--test_dir)
	    test_dir=$2
	    shift
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
	echo "USAGE: $0 [-cp|--correct_progs] [-e|--enum_all] [-ipa|--ipa labX/exY] [-o|--output_dir out_dir/] [-ss|--second_step] [-c|--cpack_ipas] [-t|--tcas] [--iscas] [-td|--test_dir dir/] [-to|--timeout] [-v|--verbose] [-h|--help] [-i|--input program.c] 
    	Options:
	--> -c|--cpack_ipas -- to use C-Pack-IPAs dataset (Default).
	--> -t|--tcas -- to run CFaults on TCAS benchmark.
	--> --iscas -- To run CFaults on ICAS85 bechmark. In this benchmark, CFaults only runs the MaxSAT oracle on this benchmark.
	--> -cp|--correct_progs -- to run CFaults on correct programs. With this option, CFaults uses the entire test suite.	
	--> -a|--enum_all -- Enumerates all the WCNF solutions, even the ones with nonoptimum cost.
	--> -e|--ipa labX/exY -- The name of C-Pack-IPA's lab and exercise. E.g. lab02/ex01
	--> -o|--output_dir out_dir/  -- path to output directory.
	--> -nu|--num_unroll NUM  -- Number to unroll the program's loops/functions. E.g. -nu 3.
	--> -ss|--second_step -- Instrumentalizes the programs a second time introducing nondeterminism.
	--> -td|--test_dir test_dir/ -- to specify the path to the test suite
	--> -to|--timeout 3600s -- to specify the timeout for CBMC, RC2, in seconds. The default is 3600s.
	--> -v|--verbose -- Set level of verbosity
	--> -h|--help -- to print this message
	--> -i|--input program.c|circuit.wcnf  -- the path to the input program/wcnf formula"
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

if [[ $ISCAS == 0 ]];
then
    CFaults_pipeline
else
    CFaults_pipeline_4_ISCAS
fi


