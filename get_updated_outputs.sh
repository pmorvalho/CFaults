#!/usr/bin/env bash
#Title			: get_updated_outputs.sh
#Usage			: bash get_updated_outputs.sh
#Author			: pmorvalho
#Date			: July 17, 2023
#Description		: Generates the updated output for each IO tests after unrolling each reference implementation with our own print functions.
#Notes			: We do this because some output changes a bit, like printing floats (e.g. 1.80000 becomes 1.79999) using our print functions for CBMC.
# (C) Copyright 2023 Pedro Orvalho.
#==============================================================================

dataset="C-Pack-IPAs"
ref_progs=$dataset/"reference_implementations"

new_test_dir="tests_updated"
unrolled_ref_progs="unrolled_reference_implementations"
labs=("lab02")
initial_dir=$(pwd)
for((l=0;l<${#labs[@]};l++));
   do
       lab=${labs[$l]}
       for ex_dir in $(find $dataset/tests/$lab/ex* -mindepth 0 -maxdepth 0 -type d);
       do
	   ex=$(echo $ex_dir | rev | cut -d '/' -f 1 | rev)
	   echo "Dealing with $lab/$ex"
	   for t in $(find $ex_dir/*.in -mindepth 0 -maxdepth 0 -type f);
	   do
	       tid=$(echo $t | rev | cut -d '/' -f 1 | cut -d '_' -f 1 | cut -d '.' -f 2 | rev)
	       mkdir -p $new_test_dir/$lab/$ex/ $unrolled_ref_progs
	       cp $t $new_test_dir/$lab/$ex/.
	       new_p=$lab-$ex-t$tid".c"
	       python3 program_unroller.py -ip $ref_progs/$lab/$ex".c" -o $new_p -e $lab/$ex -na -upt -t $tid
	       gcc $new_p $initial_dir/"prints.c" -lm
	       timeout 2s ./a.out > $new_test_dir/$lab/$ex/$ex"_"$tid".out"
	       mv $new_p $unrolled_ref_progs/.	       
	       echo
	       echo $lab/$ex/$tin
	       echo
	       cat $dataset/tests/$lab/$ex/$ex"_"$tid.in
	       echo
	       echo
	       echo "Expected Output"
	       echo
	       cat $dataset/tests/$lab/$ex/$ex"_"$tid.out
	       echo
	       echo "Generated Output"
	       echo
	       cat $new_test_dir/$lab/$ex/$ex"_"$tid".out"
	       echo
	       echo
	       echo
	   done
       done
done
rm a.out
