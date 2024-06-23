#!/usr/bin/env bash
#Title			: BugAssist.sh
#Usage			: bash BugAssist.sh -h
#Author			: pmorvalho
#Date			: January 28, 2024
#Description		: Simulates BugAssist (CAV 2011)
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

sanity_check(){
    if [[ $VERBOSE ]];
    then
	echo "Starting sanity check"
    fi
    if [[ $CORRECT_PROG == 1 ]];
    then
	tests_flags=" -upt -hw "
	if [[ $TCAS == 1 ]];
	then
	    tests_flags=$tests_flags" --test_dir $dataset_dir --traces_dir $traces_dir/$p"
	else
	    tests_flags=$tests_flags" -e $IPA "
	fi
    else
	if [[ $TCAS == 1 ]];
	then
	    tests_flags=" --test_dir $dataset_dir --traces_dir $traces_dir/$p -hw "
	else
	    tests_flags=" -t $tests_2_use -e $IPA -hw "
	    # tests_flags=" -upt -e $IPA -hw "	    
	fi
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
	python3 program_instrumentalizer.py -ip $prog -o $new_p $tests_flags -msi $stmts_map -nu $NUM_UNROLL -ssv $faults_dict -ba -fi $faults_index >& $d/"faults"/$p.pi-$faults_index-out
	# else
	#     python3 program_instrumentalizer.py -ip $prog -o $new_p -upt -e $IPA -hw  -msi $stmts_map -nu $NUM_UNROLL -ssv $faults_dict -ba -fi $faults_index >& $d/"faults"/$p.pi-$faults_index-out	    
	# fi
	
	if [[ ! ($? -eq 0) && $(grep "No more faults to relax!" $d/"faults"/$p.pi-$faults_index-out) != "" ]];
        then	    	    
	    echo "Could not find any faulty statements!"
	    echo
	    
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
	runsolver/src/runsolver -o $aux_dir/out.o -w $aux_dir/watcher.w -v $aux_dir/var.v -W $TIMEOUT --rss-swap-limit $MEMOUT cbmc/src/cbmc/cbmc $new_p prints.c --16 --unwind $NUM_UNROLL
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
	python3 get_faulty_statements.py -d $faults_dict -fi $faults_index -id $p $flag_verb -ba | tee -a $output_dir/$p.fdbk
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
	#exit
    fi    
}

Oracle(){
    # $1 filename
    # $2 mapping from instumentalized instructions to the students' instructions (pickle gzip)
    # $3 dir
    # $4 previous dir (to store the localized faults dict)
    # $5 t_num
    
    aux_dir=$3"/oracle"
    if [[ ! -d $aux_dir ]];
    then
       mkdir -p $aux_dir
    fi
    runsolver/src/runsolver -o $aux_dir/out.o -w $aux_dir/watcher.w -v $aux_dir/var.v -W $TIMEOUT --rss-swap-limit $MEMOUT python3 oracle.py --$ftype $1"."$ftype -msi $2  -ba -t $t_num --faults_dict $4
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
	if [[ $cost == "" ]];
	then
	    cost="0"
	fi	
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
    t_num=$1
    d=$2
    new_p=$3
    stmts_map=$4
    tests_flags="-t "$t_num
    if [[ $CORRECT_PROG == 1 ]];
    then
	tests_flags=$tests_flags" -upt -hw "
	if [[ $TCAS == 1 ]];
	then
	    tests_flags=$tests_flags" --test_dir $dataset_dir --traces_dir $traces_dir/$p"
	else
	    tests_flags=$tests_flags" -e $IPA "
	fi
    else
	if [[ $TCAS == 1 ]];
	then
	    tests_flags=$tests_flags" --test_dir $dataset_dir --traces_dir $traces_dir/$p -hw "
	else
	    tests_flags=$tests_flags" -e $IPA -hw "
	fi
    fi
   
    python3 program_instrumentalizer.py -ip $prog -o $new_p $tests_flags -msi $stmts_map -nu $NUM_UNROLL >& $d/$t_num.pi-out
    if [[ $? = 0 ]]; then
	gcc $d/../prints.c $d/../nondet_vals.c $new_p -o $d/$t_num.gcc-out >& $d/$t_num.pi-gcc
	if [[ $? = 0 ]]; then
	    # Next BugAssist will call CBMC
	    return
	else
	    echo "ERROR"
	    echo "Error compiling $new_p" | tee -a $d/$t_num.fdbk
	    exit
	fi
	rm $d/$t_num.gcc-out
    else
	if [[ $(grep "This program is correct according to the given set of IO tests." $d/$t_num.pi-out) != ""  ]];
	then
	    echo "FIXED $d/$p after unrolling"
	    FIXED=1
	    return
	else
	    if [[ $(grep "Warning" $d/$t_num.pi-out) ]];
	    then
		echo "FIXED: $new_p "$(grep "Warning" $d/$t_num.pi-out)
		echo $(grep "Warning" $d/$t_num.pi-out) > $d/$t_num.fdbk
		FIXED=1
		return
	    else
		echo "ERROR"
		echo "Error instrumentalizing $new_p" | tee -a $d/$t_num.fdbk
		exit
	    fi
	fi
    fi
}


BugAssist_pipeline(){
    if [[ $VERBOSE ]];
    then
	echo "Fault Localization Method: BugAssist"
    fi
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
    stmts_map=$d/$p".pkl.gz"
    faults_dict=$d"/localized_faults.pkl.gz"
    cp prints* $d/.
    cp nondet_vals.c $d/.    
    tests_list=$(find $dataset_dir/tests/$IPA/*.in -maxdepth 0 -type f);
    if [[ $CORRECT_PROG == 1 ]];
    then
	if [[ $TCAS == 1 ]];
	then
	    tests_list=$(find $dataset_dir/tests/*.in)
	fi
    else
	if [[ $TCAS == 1 ]];
	then
	    tests_list=$(find $traces_dir/$p/*.out -maxdepth 0 -type f);
	else
	    tests_2_use=$(bash check_unrolled_tests.sh $prog $dataset_dir/tests/$IPA  2> err.txt | grep -v "timeout" )
	    if [[ -f err.txt ]];
            then
                rm err.txt
            fi

	    if echo $tests_2_use | grep -v -q "\[" ;
	    then
		echo "FIXED $d/$p "$tests_2_use
		echo $tests_2_use > $d/$p.fdbk
		echo
		echo "SUCCESS"
		echo
		exit
	    fi	    
	fi
    fi
    # for each failed IO tests
    for t in $tests_list;
    do
	if [[ $TCAS == 1 ]];
	then
	    t_id=$(echo $t | rev | cut -d '/' -f 1 | rev | sed -e "s/\.out//")
	    t_num=$(echo $t_id | rev | cut -d 't' -f 1 | rev)
	else
	    t_id=$(echo $t | rev | cut -d '/' -f 1 | rev | sed -e "s/\.in//")
	    t_num=$(echo $t_id | rev | cut -d '_' -f 1 | rev)
	    # ignore passed tests
	    if [[ $CORRECT_PROG != 1 ]];
	    then
		if !(echo $tests_2_use | grep -q "$t_num") ;
		then  
		    continue;
		fi
	    fi
	fi
	if [[ $VERBOSE ]];
	then
	    echo "Checking IO test: $t_num"
	fi
	d=$output_dir
	mkdir -p $output_dir/$t_num
	cp prints* $output_dir/$t_num/.
	cp nondet_vals.c $output_dir/$t_num/. 	
	if [[ -f $output_dir/$t_num/$t_num.fdbk ]];
	then	
	    rm $output_dir/$t_num/$t_num.fdbk
	fi
       
	new_p=$output_dir/$t_num/$t_num"_instrumentalized.c"
	if [[ $VERBOSE ]];
	then
	    echo "Instrumentalizing $p using test $t_num"
	fi
	FIXED=0
	instrumentalization_step $t_num $output_dir/$t_num $new_p $stmts_map
	if [[ $FIXED -eq 1 ]];
	then
	    FIXED=0
	    continue
	fi
	if [[ $VERBOSE ]];
	then
	    echo "Calling CBMC on $p using tests $t_num"
	fi
	CBMC $new_p $output_dir/$t_num/$t_num $output_dir/$t_num
	if [[ $VERBOSE ]];
	then
	    echo "Translating the CNF into a WCNF"
	fi    
	cnf_2_wcnf_translation $output_dir/$t_num/$t_num $stmts_map
	if [[ $VERBOSE ]];
	then
	    echo "Calling the MaxSAT Oracle on $p"
	fi         
	cost=$(Oracle $output_dir/$t_num/$t_num $stmts_map $output_dir/$t_num $faults_dict $t_num)
	if [[ -f $output_dir/$t_num/oracle/out.o && $VERBOSE -eq 1 ]];
	then
	    echo $(grep "Diagnoses" $output_dir/$t_num/oracle/out.o)
	fi
	if [[ $cost == "UNSAT" ]];
	then
	    echo "UNSAT $p" | tee -a $output_dir/$p.fdbk
	    exit
	fi
	if [[ $cost == "0" && $CORRECT_PROG == "" ]];
	then
	    CBMC_bounds_check $new_p $output_dir/$t_num $output_dir/$t_num/$t_num
	fi
	rm $output_dir/$t_num/prints* $output_dir/$t_num/nondet_vals.c
    done
    
    d=$output_dir
    sanity_check
    echo
}

tests_2_use=""
FIXED=0
while [[ $# -gt 0 ]]
do
key="$1"
case $key in
    -c|--cpack_ipas)
	    CPACKIPAS=1
	    TCAS=0
	    # ISCAS=0
	    shift
    ;;

    -cp|--correct_progs)
	    CORRECT_PROG=1
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
    -t|--tcas)
	    TCAS=1
	    CPACKIPAS=0
	    # ISCAS=0
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
	echo "USAGE: $0 [-cp|--correct_progs] [-e|--enum_all] [-ipa|--ipa labX/exY] [-o|--output_dir out_dir/] [-c|--cpack_ipas] [-t|--tcas] [-td|--test_dir dir/] [-to|--timeout] [-v|--verbose] [-h|--help] [-i|--input program.c] 
    	Options:
	--> -c|--cpack_ipas -- to use C-Pack-IPAs dataset (Default).
	--> -t|--tcas -- to run BugAssist on TCAS benchmark.
	--> -cp|--correct_progs -- to run BugAssist on correct programs. With this option, BugAssist uses the entire test suite.	
	--> -a|--enum_all -- Enumerates all the WCNF solutions, even the ones with nonoptimum cost.
	--> -e|--ipa labX/exY -- The name of C-Pack-IPA's lab and exercise. E.g. lab02/ex01
	--> -o|--output_dir out_dir/  -- path to output directory.
	--> -nu|--num_unroll NUM  -- Number to unroll the program's loops/functions. E.g. -nu 3.
	--> -td|--test_dir test_dir/ -- to specify the path to the test suite
	--> -to|--timeout 3600s -- to specify the timeout for CBMC, RC2, in seconds. The default is 3600s.
	--> -v|--verbose -- Set level of verbosity
	--> -h|--help -- to print this message
	--> -i|--input program.c|circuit.wcnf  -- the path to the input program/wcnf formula"
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

BugAssist_pipeline


