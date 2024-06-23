#!/usr/bin/env bash
#Title			: check_unrolled_tests.sh
#Usage			: bash check_unrolled_tests.sh prog.c test_dir/
#Author			: pmorvalho
#Date			: October 19, 2023
#Description		: Checks on which tests (original and updated tests) the program is incorrect once unrolled
#Notes			: 
# (C) Copyright 2023 Pedro Orvalho.
#==============================================================================

initial_dir=$(pwd)
prog_2_check=$1
test_dir=$2


prog_name=$(echo $prog_2_check | rev | cut -d '/' -f 1 | rev | sed -e "s/\.c//")
# wdir="wdir_"$prog_name
wdir="/tmp/wdir_"$prog_name

if [[ ! -d $wdir ]]; then
    mkdir -p $wdir
fi

cp $prog_2_check $wdir/$prog_name".c"
cp prints.* $wdir/.
cp nondet_vals.c $wdir/.
cd $wdir
failed_tests=""
output_str=""
gcc $prog_name".c" prints.c -o prog_2_check.out 2> war.txt

clang-tidy --checks=clang-analyzer-valist.Uninitialized  $prog_name".c" >& unit_vars.log
unit_vars=$(cat unit_vars.log | grep "declared without an initial value" | grep -oh "note: .* declared" | grep -oh "'.*'" | sort -u )
if [[ $unit_vars != "" ]];
then
    echo "The following variables have not been initialized: $unit_vars "
    exit 1
fi


dbz_line=$(cat unit_vars.log | grep -A 1 "Division by zero" | tail -n 1)
if [[ $dbz_line != "" ]];
then
    echo "Warning: Divison By Zero in: '$dbz_line'"
    exit 1
fi

cppcheck -q $prog_name".c" >& unit_vars.log
unit_vars=$(cat unit_vars.log | grep uninitvar |  grep -v "__l_" | grep -oh "Uninitialized variable: .* " | grep -oh ": .*$" | grep -oh " .*" | sort -u )
if [[ $unit_vars != "" ]];
then
    echo "The following variables have not been initialized: $unit_vars "    
    exit 1
fi

output_str="Presentation Error"
for t in $(find $initial_dir/$test_dir/*.in -maxdepth 0 -type f);
do
    t_id=$(echo $t | rev | cut -d '/' -f 1 | rev | sed -e "s/\.in//")
    t_num=$(echo $t_id | rev | cut -d '_' -f 1 | rev)
    timeout 10s ./prog_2_check.out < $t > "p-"$t_id".out"
    d=$(diff -w -B "p-"$t_id".out" $initial_dir/$test_dir/$t_id".out")
    if [[ $d == "" ]];
    then
	continue;
    else
	    lab=$(echo $t | rev | cut -d '/' -f 3 | rev)
	    ex=$(echo $t | rev | cut -d '/' -f 2 | rev)
	    cd $initial_dir
	    python3 program_unroller.py -ip $wdir/$prog_name".c" -o $wdir/$prog_name-$t_id.c -td tests_updated/ -t $t_num -e $lab/$ex &> $wdir/$t_id.pu_out
	    cd $wdir
	    if [[ $(grep "This program is correct according to the given set of IO tests." $t_id.pu_out) == "" ]];
	    then
		gcc $prog_name-$t_id.c prints.c nondet_vals.c -o $prog_name-$t_id.out &> out.gcc
		if [[ -s out.gcc ]];
		then
		    #cat $prog_name-$t_id.c
		    echo "Compile Time Error"
		    exit 0
		fi
		$(timeout 10s ./$prog_name-$t_id.out &> exec.out)
		if [[ -s exec.out ]];
		then
		    output_str="There seems to be a problem with scanf/printf's format string, or the printf is unreachable"
		else
		    if [[ $failed_tests == "" ]];
		    then
			failed_tests="["$t_num
		    else
			failed_tests=$failed_tests","$t_num
		    fi
		fi
	    else
		if [[ $output_str == "CORRECT" ]];
		then
		    output_str="There seems to be a problem with scanf/printf's format string"		    
		fi
	    fi	 
	fi
done
#fi
cd $initial_dir
rm -rf $wdir
if [[ $failed_tests == "" ]];
then
    echo $output_str
else    
    echo $failed_tests"]"
fi
