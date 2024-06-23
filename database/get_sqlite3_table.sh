#!/usr/bin/env bash
#Title			: get_sqlite3_table.sh
#Usage			: bash get_sqlite3_table.sh
#Author			: pmorvalho
#Date			: January 29, 2024
#Description		: Prints a SQLite3 table for fault localization results either using TCAS or CPackIPAs datasets.
#Notes			: Modified on Apr 13 2024.
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

second_entry=0
methods_names=("CFaults" "CFaults-Refined" "BugAssist" "SNIPER")
methods=("CFaults" "CFaults-Refined" "BugAssist" "SNIPER")

dataset_dir="/home/C-Pack-IPAs"
data_dir="/home/results/C-Pack-IPAs/incorrect_submissions"
# labs=("lab02" "lab03" "lab04")
labs=("lab02")
years=("year-1" "year-2" "year-3")


process_instance_CFaults(){
    state=""
    cbmc_time="NULL"
    cbmc_memory="NULL"
    oracle_time="NULL"
    oracle_memory="NULL"
    cbmc_2nd_call_time="NULL"
    cbmc_2nd_call_memory="NULL"
    opt_cost=-1
    num_bugs=-1
    num_faults_evaluated=0
    num_mcses=-1
    num_diagnoses=-1
    second_step=0
    ss_cbmc_time="NULL"
    ss_cbmc_memory="NULL"
    ss_oracle_time="NULL"
    ss_oracle_memory="NULL"
    ss_cbmc_2nd_call_time="NULL"
    ss_cbmc_2nd_call_memory="NULL"
    ss_opt_cost=-1
    ss_num_bugs=-1
    ss_num_diagnoses=-1
    time="NULL"
    memory="NULL"
    state="MISSING"
    if [[ $(grep -o "TIMEOUT=t" $instance"/var.v") != "" ]]; then
	state="TIMEOUT"
	time=$(grep -o "CPUTIME=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")
	memory=$(grep -o "MAXVM=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")
    else
	if [[ $(grep -o "MEMOUT=t" $instance"/var.v") != "" || $(grep -o "MEMOUT" $instance"/run.o") != "" ]]; then
	    state="MEMOUT"
	    time=$(grep -o "CPUTIME=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")	    
	    memory=$(grep -o "MAXVM=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")	    
	else
	    state="SUCCESS"
	    if [[ $(grep "FAILED" $instance"/run.o") ]];
	    then
		state="FAILED"		    
	    fi
	fi
    fi
    if [[ $(grep "Attempts" $instance"/run.o") ]];
    then
	num_faults_evaluated=$(cat $instance"/run.o" | grep -oh "#Attempts: [0-9]*$" | grep -oh "[0-9]*" )
    fi		
    if [[ -f $instance"/run.o" ]];
    then
    	opt_cost=$(cat $instance"/run.o" | grep -oh "o  [0-9]*$" | grep -oh "[0-9]*" | sort | tail -n 1 )		
	num_bugs=$(cat $instance"/run.o" | grep -oh "Got an initial cost of [0-9]*$" | grep -oh "[0-9]*" | tail -n 1)
    fi
    
    if [[ -f $instance"/oracle/out.o" ]];
    then
	# opt_cost=$(cat $instance"/run.o" | grep -oh "initial cost of [0-9]*$" | head -1 | grep -oh "[0-9]*" )
	num_diagnoses=$(grep -o "#Diagnoses=[0-9]*" $instance"/oracle/out.o" | grep -o "[0-9]*")
	num_mcses=$num_diagnoses
    fi
    if [[ -f $instance/"var.v" ]];
    then
 	time=$(grep -o CPUTIME=[0-9.]* $instance"/var.v" | grep -o "[0-9\.]*")
	memory=$(grep -o MAXVM=[0-9.]* $instance"/var.v" | grep -o "[0-9\.]*")
	if [[ -d $instance"/cbmc" ]];
	then    
	    cbmc_time=$(grep -o CPUTIME=[0-9.]* $instance"/cbmc/var.v" | grep -o "[0-9\.]*")
	    cbmc_memory=$(grep -o MAXVM=[0-9.]* $instance"/cbmc/var.v" | grep -o "[0-9\.]*")
	else
	    opt_cost=-1
	    num_bugs=-1
	fi
	if [[ -d $instance"/oracle" ]];
	then
	    oracle_time=$(grep -o CPUTIME=[0-9.]* $instance"/oracle/var.v" | grep -o "[0-9\.]*")
	    oracle_memory=$(grep -o MAXVM=[0-9.]* $instance"/oracle/var.v" | grep -o "[0-9\.]*")
	fi
	if [[ -d $instance"/cbmc-2nd" ]];
	then
	    cbmc_2nd_call_time=$(grep -o CPUTIME=[0-9.]* $instance"/cbmc-2nd/var.v" | grep -o "[0-9\.]*")
	    cbmc_2nd_call_memory=$(grep -o MAXVM=[0-9.]* $instance"/cbmc-2nd/var.v" | grep -o "[0-9\.]*")
	fi
	
	if [[ -d $instance"/ss-instrumentalization" ]];
	then
	    second_step=1
	    if [[ -f $instance/"ss-instrumentalization/cbmc/var.v" ]];
	    then
		ss_cbmc_time=$(grep -o CPUTIME=[0-9.]* $instance"/ss-instrumentalization/cbmc/var.v" | grep -o "[0-9\.]*")
		ss_cbmc_memory=$(grep -o MAXVM=[0-9.]* $instance"/ss-instrumentalization/cbmc/var.v" | grep -o "[0-9\.]*")
	    fi
	    if [[ -f $instance/"ss-instrumentalization/oracle/var.v" ]];
	    then
		ss_oracle_time=$(grep -o CPUTIME=[0-9.]* $instance"/ss-instrumentalization/oracle/var.v" | grep -o "[0-9\.]*")
		ss_oracle_memory=$(grep -o MAXVM=[0-9.]* $instance"/ss-instrumentalization/oracle/var.v" | grep -o "[0-9\.]*")		
	    fi	    
	    if [[ -d $instance"/ss-instrumentalization/cbmc-2nd" ]];
	    then
		ss_cbmc_2nd_call_time=$(grep -o CPUTIME=[0-9.]* $instance"/ss-instrumentalization/cbmc-2nd/var.v" | grep -o "[0-9\.]*")
		ss_cbmc_2nd_call_memory=$(grep -o MAXVM=[0-9.]* $instance"/ss-instrumentalization/cbmc-2nd/var.v" | grep -o "[0-9\.]*")
	    fi
	    if [[ -f $instance"/ss-instrumentalization/oracle/out.o" ]];
	    then
		ss_opt_cost=$(cat $instance"/ss-instrumentalization/oracle/out.o" | grep -oh "o [0-9]*$" | head -1 | grep -oh "[0-9]*" )
		ss_num_bugs=$(cat $instance"/ss-instrumentalization/oracle/out.o" | grep -oh "#Bugs: [0-9]*$" | head -1 | grep -oh "[0-9]*" )
		ss_num_diagnoses=$(grep -o "#Diagnoses=[0-9]*" $instance"/ss-instrumentalization/oracle/out.o" | grep -o "[0-9]*")
	    fi
	fi
    fi
    if [[ $opt_cost == "" ]];
    then
       opt_cost=-1
    fi
    if [[ $num_bugs == "" ]];
    then
       num_bugs=-1
    fi
    if [[ $num_diagnoses == "" ]];
    then
	num_diagnoses=-1
	num_mcses=$num_diagnoses
    fi        
    if [[ $ss_opt_cost == "" ]];
    then
       ss_opt_cost=-1
    fi
    if [[ $ss_num_bugs == "" ]];
    then
       ss_num_bugs=-1
    fi
    if [[ $ss_num_diagnoses == "" ]];
    then
	ss_num_diagnoses=-1
    fi        
    if [[ $second_entry == 1  ]]; then
	echo ","
    fi		   
    echo "('"$p_id"','"$method"','"$state"',"$time","$memory","$cbmc_time","$cbmc_memory","$oracle_time","$oracle_memory","$cbmc_2nd_call_time","$cbmc_2nd_call_memory","$opt_cost","$num_bugs","$((num_faults_evaluated+1))","$num_mcses","$num_diagnoses","$second_step","$ss_cbmc_time","$ss_cbmc_memory","$ss_oracle_time","$ss_oracle_memory","$ss_cbmc_2nd_call_time","$ss_cbmc_2nd_call_memory","$ss_opt_cost","$ss_num_bugs","$ss_num_diagnoses")"
    second_entry=1
}



process_instance_BugAssist(){
    state=""
    cbmc_time="NULL"
    cbmc_memory="NULL"
    oracle_time="NULL"
    oracle_memory="NULL"
    cbmc_2nd_call_time="NULL"
    cbmc_2nd_call_memory="NULL"
    opt_cost=-1
    num_bugs=-1
    num_faults_evaluated=0
    num_mcses=-1        
    num_diagnoses=-1
    second_step=0
    ss_cbmc_time="NULL"
    ss_cbmc_memory="NULL"
    ss_oracle_time="NULL"
    ss_oracle_memory="NULL"
    ss_cbmc_2nd_call_time="NULL"
    ss_cbmc_2nd_call_memory="NULL"
    ss_opt_cost=-1
    ss_num_bugs=-1
    ss_num_diagnoses=-1
    time="NULL"
    memory="NULL"
    state="MISSING"
    
    if [[ $(grep -o "TIMEOUT=t" `find $instance -type f -name var.v`) != "" ]]; then
	state="TIMEOUT"
	time=$(grep -o "CPUTIME=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")	    
	memory=$(grep -o "MAXVM=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")	    	
    else
	if [[ $(grep -o "MEMOUT=t" `find $instance -type f -name var.v`) != "" || $(grep -o "MEMOUT" `find $instance -type f -name run.o`) != "" ]]; then
	    state="MEMOUT"
	    time=$(grep -o "CPUTIME=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")	    
	    memory=$(grep -o "MAXVM=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")	    	    
	else
	    if [[ $(grep "UNSAT" $instance"/run.o") ]];
	    then
		state="UNSAT"
	    else
		state="SUCCESS"
		if [[ $(grep "FAILED" $instance"/run.o") ]];
		then
		    state="FAILED"		    
		fi
	    fi
	fi
     fi
    if [[ $(grep "Attempts" $instance"/run.o") ]];
    then
	num_faults_evaluated=$(cat $instance"/run.o" | grep -oh "#Attempts: [0-9]*$" | grep -oh "[0-9]*" )
    fi		

    if [[ -f $instance"/run.o" ]];
    then
	opt_cost=$(cat $instance"/run.o" | grep -oh "o  [0-9]*$" | head -1 | grep -oh "[0-9]*" )		    
	num_bugs=$(cat $instance"/run.o" | grep -oh "b  [0-9]*$" | head -1 | grep -oh "[0-9]*" )
    fi
    if [[ -f $instance/"var.v" ]];
    then
	time=$(grep -o "CPUTIME=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")
	memory=$(grep -o "MAXVM=[0-9.]*" $instance"/var.v" | grep -o "[0-9\.]*")
	if [[ $(find $instance/* -type d -name cbmc ) != "" ]];	   	   
	then    
	    cbmc_time=$(echo $(cat $instance/*/cbmc/var.v | grep -o "CPUTIME=[0-9.]*"  | grep -o "[0-9\.]*" | sed 's/$/+/') 0 | bc)
	    cbmc_memory=$(echo $(cat $instance/*/cbmc/var.v | grep -o "MAXVM=[0-9.]*"  | grep -o "[0-9\.]*" | sed 's/$/+/') 0 | bc)
	else
	    opt_cost=-1
	    num_bugs=-1
	fi
	if [[ $(find $instance/* -type d -name oracle )  != ""  ]];	   
	then
	    oracle_time=$(echo $(cat $instance/*/oracle/var.v | grep -o "CPUTIME=[0-9.]*"  | grep -o "[0-9\.]*" | sed 's/$/+/') 0 | bc)
	    oracle_memory=$(echo $(cat $instance/*/oracle/var.v | grep -o "MAXVM=[0-9.]*"  | grep -o "[0-9\.]*" | sed 's/$/+/') 0 | bc)
	    num_mcses=$(echo $(cat $instance/*/oracle/out.o | grep -o "#MCSes=[0-9]*"  | grep -o "[0-9]*" | sed 's/$/+/') 0 | bc)
	    
	fi
	if [[ $(find $instance/* -type d -name cbmc-2nd )  != ""  ]];
	then
	    cbmc_2nd_call_time=$(echo $(cat $instance/*/cbmc-2nd/var.v | grep -o "CPUTIME=[0-9.]*"  | grep -o "[0-9\.]*" | sed 's/$/+/') 0 | bc)
	    cbmc_2nd_call_memory=$(echo $(cat $instance/*/cbmc-2nd/var.v | grep -o "MAXVM=[0-9.]*"  | grep -o "[0-9\.]*" | sed 's/$/+/') 0 | bc)
	fi
    fi
    if [[ -f $instance/"run.o" && $(grep "#Diagnoses=[0-9]*" $instance"/run.o") != "" ]];
    then
	num_diagnoses=$(echo $(cat $instance/run.o | grep -o "#Diagnoses=[0-9]*"  | grep -o "[0-9]*" | sed 's/$/+/') 0 | bc)			
    fi
    if [[ $(grep "Attempts" $instance"/run.o") ]];
    then
	num_faults_evaluated=$(cat $instance"/run.o" | grep -oh "#Attempts: [0-9]*$" | grep -oh "[0-9]*" )
    fi		
    if [[ $opt_cost == "" ]];
    then
       opt_cost=-1
    fi
    if [[ $num_bugs == "" ]];
    then
       num_bugs=-1
    fi    

    if [[ $second_entry == 1  ]]; then
	echo ","
    fi
    if [[ $method == "BugAssist" ]];
    then
	num_diagnoses=$num_mcses
    fi
    echo "('"$p_id"','"$method"','"$state"',"$time","$memory","$cbmc_time","$cbmc_memory","$oracle_time","$oracle_memory","$cbmc_2nd_call_time","$cbmc_2nd_call_memory","$opt_cost","$num_bugs","$((num_faults_evaluated+1))","$num_mcses","$num_diagnoses","$second_step","$ss_cbmc_time","$ss_cbmc_memory","$ss_oracle_time","$ss_oracle_memory","$ss_cbmc_2nd_call_time","$ss_cbmc_2nd_call_memory","$ss_opt_cost","$ss_num_bugs","$ss_num_diagnoses")"    
    second_entry=1
}


CPackIPAs(){

source CPackIPAs_table.sh
    
for((r=0;r<${#methods[@]};r++));
do
    method=${methods[$r]}
    method_name=${methods_names[$r]}  
    for((y=0;y<${#years[@]};y++));
    do
	year=${years[$y]}
	for((l=0;l<${#labs[@]};l++));
	do
	    lab=${labs[$l]}
	    for ex in $(find $dataset_dir/semantically_incorrect_submissions/$year/$lab/ex* -maxdepth 0 -type d);
	    do
		ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
		for instance in $(find $data_dir/$method/$year/$lab/$ex/* -maxdepth 0 -mindepth 0 -type d);
		do
		    stu_id=$(echo $instance | rev | cut -d '/' -f 1 | rev)	    
		    p_id=$year/$lab/$ex/$stu_id
		    if [[ $method == "CFaults" || $method == "CFaults-Refined" ]];
		    then
			process_instance_CFaults
		    else
			process_instance_BugAssist
		    fi
		done
	    done
	done
    done
done

}

TCAS(){

source tcas_table.sh

for((r=0;r<${#methods[@]};r++));
do
    method=${methods[$r]}
    method_name=${methods_names[$r]}  
    for instance in $(find $data_dir/$method/* -maxdepth 0 -mindepth 0 -type d);
    do
	p_id=$(echo $instance | rev | cut -d '/' -f 1 | rev)	    
	if [[ $method == "CFaults" ||  $method == "CFaults-Refined" ]];
	then
	    process_instance_CFaults
	else
	    process_instance_BugAssist
	fi
    done
done

}
    
while [[ $# -gt 0 ]]
do
key="$1"
case $key in
    -c|--cpack_ipas)
	    CPACKIPAS=1
	    TCAS=0
	    shift
    ;;
    -t|--tcas)
	    TCAS=1
	    CPACKIPAS=0
	    dataset_dir="tcas"
	    traces_dir=$dataset_dir/"traces"
	    shift
    ;;  
    -h|--help)
	echo "USAGE: $0 [-c|--cpack_ipas] [-t|--tcas] [-h|--help] 
    	Options:
	--> -c|--cpack_ipas -- get results from C-Pack-IPAs benchmark.
	--> -t|--tcas -- get results from TCAS benchmark.
	--> -h|--help -- to print this message"
	exit
    shift
    ;;
    *)
	echo "get_sqlite3_table.sh: error: unrecognized arguments: $key"
	echo "Try [-h|--help] for help"
	shift
	exit
	;;    

esac
done

if [[ $CPACKIPAS -eq 1 ]];
then
    CPackIPAs
else if [[ $TCAS -eq 1 ]];
     then
	 TCAS
     else
	echo "get_sqlite3_table.sh: error: unrecognized arguments: $key"
	echo "Try [-h|--help] for help"
	exit	 
     fi
fi

echo ";"
