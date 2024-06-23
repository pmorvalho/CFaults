#!/usr/bin/python
#Title			: get_fault_loc_results.py
#Usage			: python get_fault_loc_results.py -h
#Author			: pmorvalho
#Date			: April 12, 2024
#Description		: Prints a table with the fault localization results for CFaults and BugAssist
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

import os
import sqlite3
import pandas as pd

def query_db(condition="", lab=None, fault_loc_method=None):
    global table
    cond=""
    if fault_loc_method is not None:
        cond += " fault_loc_method = '"+fault_loc_method+"' "
    cond += condition
    with sqlite3.connect('results.db') as connection: 
        df = pd.read_sql('select program_id, fault_loc_method, time from {t} where {c};'.format(t=table,c=cond), connection).reset_index()
        return len(df.index)
        
def print_results(fault_loc_method, timeout=60, lab=None):
    res="\\textbf{"+fault_loc_method+"} & "
    total=0
    succ = query_db(condition="and time < {t} and state = 'SUCCESS'".format(t=timeout), lab=lab, fault_loc_method=fault_loc_method)
    total += succ
    res+="& "    
    res+= "{t} ({t_p}\%) & ".format(t=succ, t_p=round(100*succ/query_db(lab=lab, fault_loc_method=fault_loc_method),2))


    #failed = query_db(condition="and state = 'FAILED'", lab=lab, fault_loc_method=fault_loc_method)
    #res+= "{t} ({t_p}\%) & ".format(t=failed, t_p=round(100*failed/query_db(lab=lab, fault_loc_method=fault_loc_method),2))   
    #total += failed    

    memout = query_db(condition="and state = 'MEMOUT'", lab=lab, fault_loc_method=fault_loc_method)
    res+="& "    
    res+= "{t} ({t_p}\%) & ".format(t=memout, t_p=round(100*memout/query_db(lab=lab, fault_loc_method=fault_loc_method),2))
    total += memout
    
    timeouts = query_db(condition="and ((time >= {t} and state != 'FAILED') or state = 'TIMEOUT')".format(t=timeout), lab=lab, fault_loc_method=fault_loc_method)
    res+="& "    
    res+= "{t} ({t_p}\%)\\\\".format(t=timeouts, t_p=round(100*timeouts/query_db(lab="lab02", fault_loc_method=fault_loc_method),2))
    total += timeouts                              

    print(res)
#    assert(total == number_of_programs)

                                
if __name__ == '__main__':

    if not os.path.isdir("tables"):
        os.system("mkdir tables")        
    TIMEOUT=3600
    l_name = ["Lab 02"]
    # , "Lab 03", "Lab 04"]
    labs = ["lab02"]
    # , "lab03", "lab04"]
    tables = ["TCAS", "C-Pack-IPAs"]
    #print("\\toprule")
    #print("\multicolumn{5}{c}{\\textbf{Fault Localization}} \\\\ \\hline")
   # print("\multicolumn{4}{c}{\\textbf{Fault Localization}} \\\\ \\hline")    
    print()
    for t in tables:
        table = "tcas" if t == "TCAS" else "CPackIPAs"
        for l in range(len(labs)):
            lab_name = l_name[l]
            lab = labs[l]
            number_of_programs = query_db(fault_loc_method="CFaults", lab=lab)
            # print(lab_name)
            # print()
            # print()
            # print("\\toprule")
            #print("\multicolumn{5}{c}{} \\\\")
            #print("\multicolumn{5}{c}{Benchmark: \\textbf{"+t+"}} \\\\ \\hline")
            #print("{} & \\textbf{Success}  & \\textbf{Failed} &  \\textbf{Memouts (32Gb)} & \\textbf{Timeouts ("+str(TIMEOUT)+"s)}\\\\")
            print("\multicolumn{7}{c}{} \\\\")
            print("\\toprule")
            print("\multicolumn{7}{c}{Benchmark: \\textbf{"+t+"}} \\\\ \\hline")
            print("{} && \\begin{tabular}[c]{@{}c@{}}\\textbf{Valid}\\\\\\textbf{Diagnosis}\\end{tabular} &&  \\textbf{Memouts} && \\textbf{Timeouts}\\\\")
            #print("{} & \\textbf{Success} &  \\textbf{Memouts (32Gb)} & \\textbf{Timeouts ("+str(TIMEOUT)+"s)}\\\\")            
            print("\\hline")
            # BugAssist
            print_results("BugAssist", timeout=TIMEOUT, lab=lab)
            # SNIPER
            print_results("SNIPER", timeout=TIMEOUT, lab=lab)            
            # CFaults
            print_results("CFaults", timeout=TIMEOUT, lab=lab)
            print_results("CFaults-Refined", timeout=TIMEOUT, lab=lab)
            # print("\\bottomrule")
            print()
            print()
    print("\\bottomrule")
    #print("\multicolumn{5}{c}{} \\\\")
    print("\multicolumn{7}{c}{} \\\\")
