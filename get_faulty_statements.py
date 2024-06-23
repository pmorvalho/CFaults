#!/usr/bin/python
#Title			: get_faulty_statements.py
#Usage			: python get_faulty_statements.py -h
#Author			: pmorvalho
#Date			: March 20, 2024
#Description		: Given an index returns the set of faulty statements.
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

import argparse
from sys import argv
from helper import *


def get_faults():
    d = load_dict(args.d)
    num_lines = -1
    for k in d.keys():    
        if args.bug_assist:
            try:
                top_choice = list(d[k]["top_choice"][args.fault_index][0])
                for k2 in d[k].keys():
                    if k2 == "MCSes" or k2 == "top_choice":
                        continue
                    
                    for i in range(len(d[k][k2])):
                        if 'linenos' not in d[k][k2][i].keys():
                            continue
                        if d[k][k2][i]['linenos'] == set(top_choice):
                            # faults = [e[2] for e in d[k][k2][i]["faults"] if "There is a missing" not in "".join(e[2])]
                            faults = [e[2] for e in d[k][k2][i]["faults"]]
                            cost = d[k][k2][i]["cost"]
                            num_lines = len(d[k][k2][i]["lines"])
                            break
            except:
                faults = [["There seems to be some sort of out-of-bounds memory access!"]]
                cost = 0
                num_lines = 1                                                 
        elif args.sniper:
            try:
                top_choice = d[k]["top_choice"][args.fault_index]
                cost = top_choice["cost"]
                num_lines  = top_choice["num_lines"]
                linenos = top_choice["linenos"]
                faults = top_choice["lines"]
                key = top_choice["key"]
            except:
                faults = [["There seems to be some sort of out-of-bounds memory access!"]]
                cost = 0
                num_lines = 1                                                 
        else:
            top_choice = d[k][args.fault_index]
            # faults = [e[2] for e in top_choice["faults"] if "There is a missing" not in "".join(e[2])]
            if "faults" in top_choice.keys():
                faults = [e[2] for e in top_choice["faults"]]
                cost = top_choice["cost"]
                num_lines = len(top_choice["lines"])
            else:
                faults = [["There seems to be some sort of out-of-bounds memory access!"]]
                cost = top_choice["cost"]
                num_lines = 1                                 

    tuple_lists = [tuple(sublist) for sublist in faults]
    # Use set to remove duplicates
    unique_tuples = set(tuple_lists)
    # Convert tuples back to lists
    faults = [list(t) for t in unique_tuples]
    if args.verbose:
        print('o ', cost)
        print('b ', num_lines)    
    print('Successfully localized',len(faults),'faults in ', args.id, ".")
    print()
    print("The following program line(s) should be carefully analyzed:")
    for f in faults:
        if len(f) == 1:
            print("- ", str(f[0]).replace("\n", "\\n"))
        else:
            print("- ", end="")
            for ff in f:
                print(str(ff).replace("\n", "\\n"),end="")
                print(" OR ", end="")
            print()

def parser():
    parser = argparse.ArgumentParser(prog='get_faulty_statements.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', nargs='?', help='input dictionary.')
    parser.add_argument('-ba', '--bug_assist', action='store_true', default=False, help='Check BugAssist\'s results.')
    parser.add_argument('--sniper', action='store_true', default=False, help='Check SNIPER\'s results.')        
    parser.add_argument('-fi', '--fault_index', type=int, default=0, help='Index of the set of faults enumerated.')
    parser.add_argument('-id', help='program id.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args

if __name__ == '__main__':
    args = parser()
    get_faults()
