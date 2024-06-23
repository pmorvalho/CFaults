#!/usr/bin/python
#Title			: oracle.py
#Usage			: python oracle.py -h
#Author			: pmorvalho
#Date			: March 07, 2023
#Description		: RC2 Solver, returns which lines should be removed
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2023 Pedro Orvalho.
#==============================================================================

import argparse
from sys import argv
from pwcnf import PWCNF
from pysat.formula import WCNF, CNF
from pysat.examples.mcsls import MCSls
from pysat.examples.rc2 import RC2, RC2Stratified
from pysat.solvers import Solver
from helper import *
import time

class UpRC2(object):
    """
       RC2 Solver Solver for PWCNFs based on user partitioning of the soft clauses.
       Calls RC2 #n_partitions times, adding each set of user-defined partitions incrementally.
    """
    def __init__(self, pwcnf, no_up=False):
        """
            Constructor.
        """
        self.pwcnf = pwcnf
        #self.rc2 = RC2Stratified(WCNF())
        self.rc2 = RC2(WCNF(), blo='full')
        self.no_up = no_up
        
    def compute(self):
        """
           Computes either using user-based partitions or not
        """
        if not self.no_up:
            return self.compute_with_partitions()
        else:
            return self.compute_without_partitions()
        
    def compute_with_partitions(self):
        """
            Calls RC2 #n_partitions times, adding each set of user-defined partitions incrementally.
        """    
        m = self.rc2.compute()        
        for h in self.pwcnf.get_hard():
            self.rc2.add_clause(h)
            
        m = self.rc2.compute()
        for j in range(len(self.pwcnf.get_partitions())):
            p_clauses, wghts = self.pwcnf.get_partition(j), self.pwcnf.get_partition_weights(j)
            for i in range(len(p_clauses)):
                c, w = p_clauses[i], wghts[i]
                # if args.verbose:
                #     print("Adding ", c)
                self.rc2.add_clause(c, weight=w)
            # if args.verbose:
            #     print("Computing model")
            m = self.rc2.compute()
        return m, self.rc2.cost

    def compute_without_partitions(self):
        """
            Calls RC2 ignoring the user-defined partitions i.e. adds all the hard and soft clauses at once.
        """
        m = self.rc2.compute()                
        for h in self.pwcnf.get_hard():
            self.rc2.add_clause(h)
            
        for i in range(len(self.pwcnf.get_soft())):
            c, w = self.pwcnf.get_soft_clause(i), self.pwcnf.get_soft_weight(i)
            self.rc2.add_clause(c, weight=w)
        m = self.rc2.compute()
        return m, self.rc2.cost    


def get_faults_info(m, pwcnf, m_2_block=None):
    subset_info=dict()
    lines=dict()
    cost = 0
    output_str = ""
    for l in m:        
        if -l in pwcnf.soft_vars:
            if m_2_block != None:
                m_2_block.append(-l)
            l_v = "\'{l}\'".format(l=-1*l) if map_stmts else str(-1*l)
            for v in lits_per_lines.keys():
                if l_v in lits_per_lines[v]:                    
                    i = lits_per_lines[v].index(l_v)
                    if v not in lines.keys():
                        if i < 8:
                            lines[v] = [(l, 0)] if len(lits_per_lines[v]) > 8 else [(l, None)]
                        else:
                            lines[v] = [(l, int((i+1)/8)-1)]
                        if args.verbose:
                            print(lines[v])
                    else:
                        i = 0 if i < 8 else int((i + 1)/ 8) - 1
                        lines[v].append((l,i))
                        if args.verbose:
                            print("Adding more iterations to ", v, lines[v])                             
                    break

    if args.verbose:
        print(lines)
    subset_info["lines"] = lines
    subset_info["num_faults"] = 0
    if lines:
        output_str += "Remove: \n"
        subset_info["faults"] = []
        subset_info["linenos"] = []        
        for v in lines.keys():
            for l, i in lines[v]:
                # the above l is the literal is the WCNF
                if map_stmts != None:
                    pl, w, s = map_stmts[v]
                    pl=pl-1
                    cost += w
                    if i is None:
                        output_str += "Weight: {w} Lineno: {pl} Statement: {s}.\n".format(w=w, pl=pl, s=s[0] if len(s) == 0 else " OR ".join(s))
                        subset_info["faults"].append([w,pl,s,None,v])
                        subset_info["linenos"].append(pl)
                    else:
                        output_str += "Weight: {w} Lineno: {pl}  Statement: {s} after {i} iterations.\n".format(w=w, pl=pl ,s=s[0] if len(s) == 0 else " OR ".join(s), i=i)
                        if len(s) == 0:
                            s[0] = s[0] + " after {i} iterations".format(i=i)
                        subset_info["faults"].append([w,pl,s,i,v])
                        subset_info["linenos"].append(pl)
                else:
                    if i == 0:
                        output_str += str(v)
                    else:
                        output_str += str(v)+" after "+str(i)+" iterations.\n"              
        subset_info["num_faults"] = len(subset_info["faults"])
        subset_info["linenos"] = set(subset_info["linenos"])
        print("#Bugs:",len(subset_info["linenos"]))
        print()
        print(output_str)
        subset_info["cost"] = cost        
    return subset_info
    
def enumerate_MCSes(wcnf, pwcnf, rc2, faults, test_id, only_first_solution=False):    
    # enumerate minimal correction subsets (MCSes)
    if args.verbose:
        print("Enumerating MCSes - SNIPER/BugAssist")

    if stu_id not in faults.keys():        
        faults[stu_id] = dict()
    if "MCSes" not in faults[stu_id].keys():
        faults[stu_id]["MCSes"] = dict()
    if "top_choice" not in faults[stu_id].keys():
        faults[stu_id]["top_choice"] = list()
        
    faults[stu_id][test_id] = []
    
    n_mcs = 0
    start = time.time()    
    for m in rc2.enumerate(block=-1):        
        end = time.time()
        loc_time = end - start
        if n_mcs == 0 and args.verbose:
            print("Time spent localizing faults:", loc_time)

        mcs = dict()
        c = rc2.cost        
        n_mcs += 1
        m_2_block = []
        print()
        print('s OPTIMUM FOUND #', n_mcs)
        print('o', str(c))
        print('t', str(round(loc_time,2)), '(s)')
        mcs = get_faults_info(m, pwcnf, m_2_block)
        mcs["time"] = loc_time
        mcs["cost"] = c

        if "linenos" in mcs.keys() and "lines" in mcs.keys():
            s = frozenset(mcs["linenos"])
            s2 = []
            for k in mcs["lines"].keys():
                for l, i in mcs["lines"][k]:
                    s2.append((k,i))
            s2 = frozenset(s2)

            if (s,s2,mcs["cost"]) not in faults[stu_id]["MCSes"].keys():
                faults[stu_id]["MCSes"][(s,s2,mcs["cost"])] = 1
            else:
                faults[stu_id]["MCSes"][(s,s2,mcs["cost"])] += 1

        faults[stu_id][test_id].append(mcs)
        if only_first_solution:
            break
        start = time.time()
        
    keys_with_max_count = list(faults[stu_id]["MCSes"].items())
    # print(faults[stu_id]["MCSes"])
    # print(keys_with_max_count)
    # print()
    keys_with_max_count = sorted(keys_with_max_count, key=lambda d: len(d[0][1]))
    # print("len", keys_with_max_count)
    # print()    
    keys_with_max_count = sorted(keys_with_max_count, key=lambda d: d[0][2])
    # print("Cost", keys_with_max_count)
    # print()
    keys_with_max_count = sorted(keys_with_max_count, key=lambda d: d[1], reverse=True)
    # print("counter", keys_with_max_count)
    # print()    
    keys_with_max_count = [(key[0], key[1]) for key, value in keys_with_max_count]
    # print(keys_with_max_count)
    # print()    
    faults[stu_id]["top_choice"] = keys_with_max_count

    print("All MCSes enumerated!")    
    print("#MCSes={n}".format(n=n_mcs))
    if args.bug_assist:
        print("#Diagnoses={n}".format(n=len(keys_with_max_count)))
    return faults
    
def enumerate_MaxSATsolutions(wcnf, pwcnf, rc2, faults, only_first_solution=False, enum_all=False):    
    # enumerate MaxSAT solutions
    faults[stu_id] = []    
    n_comss = 0
    opt_weight = -1
    while True:
        start = time.time()
        m = rc2.compute()
        c = rc2.cost
        end = time.time()
        loc_time = end - start        
        if n_comss == 0:
            opt_weight = c
        co_mss = dict()
        if (c > opt_weight and not enum_all) or not m:
            break
        n_comss += 1
        m_2_block = []
        print()
        print('s OPTIMUM FOUND #', n_comss)
        print('o', str(c))
        print('t', str(round(loc_time,2)), '(s)')        

        co_mss = get_faults_info(m, pwcnf, m_2_block)
        co_mss["time"] = loc_time # rc2.oracle_time()        
        co_mss["cost"] = c

        faults[stu_id].append(co_mss)
        # print(m_2_block)

        if only_first_solution:
            break        
        rc2.add_clause(m_2_block)        
        
    print("All MaxSAT solutions enumerated!")
    print("#Diagnoses={n}".format(n=n_comss))
    faults[stu_id] = sorted(faults[stu_id], key=lambda d: len(d["lines"].keys()))
    # print([len(f['lines']) for f in faults[stu_id]])
    # print()
    # we do not need the following for MaxSAT solutions
    # faults[stu_id] = sorted(faults[stu_id], key=lambda d: d["cost"])
    return faults
    
def parser():
    parser = argparse.ArgumentParser(prog='oracle.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--pwcnf', help='PWCNF formula.')
    parser.add_argument('-nup', '--no_up', action='store_true', default=False, help='Calls the MaxSAT solver (RC2) using the PWCNF formula without considering the partitions present in the formula.')
    parser.add_argument('-a', '--enum_all', action='store_true', default=False, help='Enumerates all the MaxSAT solutions. Even the ones without the opt cost.')
    parser.add_argument('-f', '--only_first_solution', action='store_true', default=False, help='Enumerates only the first MaxSAT solution.')    
    parser.add_argument('-ba', '--bug_assist', action='store_true', default=False, help='Enumerates all the MCSes of the WCNF, using PySAT MCS enumerator MCSls.')
    parser.add_argument('--sniper', action='store_true', default=False, help='Check SNIPER\'s results.')        
    parser.add_argument('-t', '--test_id', nargs='?', help='IO test id.')
    parser.add_argument('--wcnf', help='WCNF formula.')
    parser.add_argument('--cnf', help='CNF formula.')
    parser.add_argument('-msi', '--map_stu_insts', nargs='?', help='Path to the mapping from instrumentalized-unrolled program statements to the original students\' instructions.')
    parser.add_argument('-fd', '--faults_dict', nargs='?', help='Path to the dictionary where the faults are supposed to be stored at.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')    
    args = parser.parse_args(argv[1:])
    return args

if __name__ == '__main__':
    args = parser()
    stu_id = None
    if args.pwcnf:
        stu_id = args.pwcnf.replace(".pwcnf", "").replace(".gz", "").split("/")
        pwcnf = PWCNF(from_file=args.pwcnf)
    elif args.wcnf:
        stu_id = args.wcnf.replace(".wcnf", "").replace(".gz", "").split("/")
        wcnf = WCNF(from_file=args.wcnf)
        pwcnf = PWCNF(from_file=args.wcnf, wcnf=True)
        args.no_up = True
    elif args.cnf:
        cnf = CNF(from_file=args.cnf)
        s = Solver(bootstrap_with=cnf)        
        if s.solve():
            exit("SAT")
        else:
            exit("UNSAT")

    if "_" in stu_id[-1] and len(stu_id) > 4:
        i = stu_id[-1].split("-")
        stu_id = "{y}#{l}/{e}#{s}#{su}".format(y=stu_id[-5],l=stu_id[-4],e=i[-3],s=i[-2],su=i[-1])
    elif (args.bug_assist or args.sniper) and len(stu_id) > 5 and "_" in stu_id[-3]:
        i = stu_id[-3].split("-")
        stu_id = "{y}#{l}/{e}#{s}#{su}".format(y=stu_id[-6],l=stu_id[-5],e=stu_id[-4],s=i[-2],su=i[-1])   
    elif (args.bug_assist or args.sniper) and len(stu_id) > 2:
        stu_id = stu_id[-3]
    else:
        stu_id = stu_id[-1]
    
    print("Instance:", stu_id)
    map_stmts = load_dict(args.map_stu_insts) if args.map_stu_insts != None else None
    try:
        faults = load_dict(args.faults_dict)
    except:
        faults = dict()
        pass
    
    lits_per_lines=dict()
    with open(args.wcnf if args.wcnf != None else args.pwcnf, "r+") as f:
        for l in f.readlines():
            if "[" in l:
                v, l = l.split("[")
                v = v.split(" ")[1]
                lst = list(l[:-2].split(", "))
                if v not in lits_per_lines.keys():
                    lits_per_lines[v] = lst
                else:
                    lits_per_lines[v] += lst
    if args.verbose:
        print(len(lits_per_lines), lits_per_lines)
    if args.pwcnf:
        rc2 = UpRC2(pwcnf, no_up=args.no_up)
        faults = enumerate_MaxSATsolutions(wcnf, pwcnf, rc2, faults)
    elif args.bug_assist or args.sniper:        
        rc2 = RC2Stratified(wcnf)
        rc2.hard = False
        # rc2 = RC2(wcnf)
        faults = enumerate_MCSes(wcnf, pwcnf, rc2, faults, args.test_id, args.only_first_solution)
    else:
        rc2 = RC2Stratified(wcnf)
        rc2.hard = False        
        faults = enumerate_MaxSATsolutions(wcnf, pwcnf, rc2, faults, args.only_first_solution, args.enum_all)

    if args.verbose:
        print(faults.keys())
        if not args.bug_assist and not args.sniper:
            print(faults[stu_id][0]["linenos"])
        else:
            print(faults[stu_id])
    save_dict(faults, args.faults_dict)
