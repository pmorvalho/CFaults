#!/usr/bin/python
#Title			: compute_cartesian_product_MCSes.py
#Usage			: python compute_cartesian_product_MCSes.py -h
#Author			: pmorvalho
#Date			: March 28, 2024
#Description		: Compute the Cartesian product of all MCSes (sets of faulty lines) from each failing tests
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

import argparse
from sys import argv
from itertools import product
from helper import *

def compute_cartesian_prod_MCSes():
    d = load_dict(args.d)
    msi = load_dict(args.map_stu_insts)
    new_top_choice = []
    mcses_per_test = dict()
    mcses_to_ids = dict()
    ids_to_mcses = dict()
    for k in d.keys():
        for t in d[k].keys():
            if t == "MCSes" or t == "top_choice":
                continue
            for i in range(len(d[k][t])):
                fs = frozenset([(k, v1) for k, v in d[k][t][i]["lines"].items() for v0, v1 in v])
                # fs = frozenset([(k, v[0][1]) for k, v in d[k][t][i]["lines"].items()])
                if fs not in mcses_to_ids.keys():
                    new_i = len(mcses_to_ids.items())
                    mcses_to_ids[fs] = new_i
                    ids_to_mcses[new_i] = fs
                if t not in mcses_per_test.keys():                        
                    mcses_per_test[t] = [mcses_to_ids[fs]]
                else:
                    mcses_per_test[t].append(mcses_to_ids[fs])

        if args.verbose:
            print("MCSes per test:", mcses_per_test)
            print(mcses_to_ids)

        # Extract the values from the dictionary
        values = [set(v) for v in mcses_per_test.values()]

        # Calculate the Cartesian product
        cartesian_product = list(product(*values))
        if args.verbose:
            print("Cartesian Prod:", cartesian_product)
        
        products=list()
        for x in cartesian_product:
            s = set(x)
            if s not in products:
                products.append(s)
        
        if args.verbose:
            print("Final sets:", products)
        f = []
        for p in products:
            prod = []
            for e in list(p):
                for v in ids_to_mcses[e]:
                    prod.append(v)
            f.append(set(prod))
        
        for ff in f:
            cost = 0
            linenos = []
            lines = []
            for kk, _ in ff:
                ln, c, l = msi[kk]
                cost += c
                linenos.append(ln)
                if l not in lines:
                    lines += [l]
            choice = dict()
            choice["cost"] = cost
            choice["num_lines"] = len(set([l for l, _ in ff]))
            choice["linenos"] = set(linenos)
            choice["lines"] = lines
            choice["key"] = ff
            new_top_choice.append(choice)

        # new_top_choice = sorted(new_top_choice, key=lambda d: len(d["lines"]))
        # new_top_choice = sorted(new_top_choice, key=lambda d: d["cost"])

        new_top_choice = sorted(new_top_choice, key=lambda d: len(d["key"]))        
        new_top_choice = sorted(new_top_choice, key=lambda d: d["cost"])

        d[k]["top_choice"] = new_top_choice
        print("#Diagnoses={n}".format(n=len(new_top_choice)))                        
        if args.verbose:
            # print(new_top_choice)
            for tc in new_top_choice:
                print(tc["linenos"])
                break

        save_dict(d, args.d)

def parser():
    parser = argparse.ArgumentParser(prog='compute_cartesian_product_MCSes.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', nargs='?', help='input dictionary.')
    parser.add_argument('-msi', '--map_stu_insts', nargs='?', help='Path to the mapping from instrumentalized-unrolled program statements to the original students\' instructions.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args

if __name__ == '__main__':
    args = parser()
    compute_cartesian_prod_MCSes()
