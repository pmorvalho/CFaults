#!/usr/bin/python3
#Title			: data_2_plots.py
#Usage			: python data_2_plots.py -h
#Author			: pmorvalho
#Date			: April 01, 2024
#Description		: Queries the database for the fault loc table with all GL methods. Saves a csv file for the cactus and scatter plot.
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2024 Pedro Orvalho.
#==============================================================================

from sys import argv
import pandas as pd
import sqlite3
import os
import os.path
import concurrent.futures
from itertools import combinations
from subprocess import Popen, PIPE
import sys

TIMEOUT=3600
XMIN=0.1

def gen_plot(args):
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    try:
        outs, errs = proc.communicate(timeout=15)
    except TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
        
def gen_scatter_plot(args):
    df, max_num, m, lb, xmin, t = args
    methods=df.columns
    name = '{tb}-scatter-{m}-{m0}-{m1}'.format(tb=t,m=m,m0=methods[0], m1=methods[1])
    name = name.replace(" ","_")
    df.to_csv("csvs/{n}.csv".format(n=name),index_label=None)
    args = ["python3", "../mkplot/mkplot.py",
            "-p", "scatter",
            "--ylog", "--xlog",
            "--xmin={x}".format(x=xmin),
            "--xmax={x}".format(x=max_num+10),            
            "--shape", "squared",
            "--timeout={t}".format(t=max_num*1.01),
            "--tlabel={t} {lb}".format(t=max_num, lb=lb) if lb != "memout/timeout" else "--tlabel={lb}".format(lb=lb),
            "--lloc=left"]
                        
    gen_plot(args + ["-b", "svg", "--save-to", "plots/{n}.svg".format(n=name), "csvs/{n}.csv".format(n=name)])
    gen_plot(args + ["-b", "pdf", "--save-to", "plots/{n}.pdf".format(n=name), "csvs/{n}.csv".format(n=name)])
    
def gen_cactus_plot(df, tb, m, mn, max_num, xmin=None):
    df.to_csv('csvs/{tb}-cactus-{m}.csv'.format(tb=tb,m=m),index_label=None)
    args = ["python3", "../mkplot/mkplot.py",
            "-p", "cactus",
            "--shape", "squared",
            "--ylabel="+mn,
            "--xlabel=#Programs",
            "--timeout={t}".format(t=int(max_num*1.01)),
            "--lloc=upper left",
            # "--xmax={x}".format(x=max_num)]
            "--xmax={x}".format(x=len(df))]
    # if xmin:
    #     args.append("--xmin={x}".format(x=xmin))
            
    gen_plot(args + ["-b", "svg","--save-to", 'plots/{tb}-cactus-{m}.svg'.format(tb=tb,m=m), 'csvs/{tb}-cactus-{m}.csv'.format(tb=tb,m=m)])
    gen_plot(args + ["-b", "pdf","--save-to", 'plots/{tb}-cactus-{m}.pdf'.format(tb=tb,m=m), 'csvs/{tb}-cactus-{m}.csv'.format(tb=tb,m=m)])

    
def main():
    if not os.path.isdir("plots"):
        os.system("mkdir plots")
    if not os.path.isdir("csvs"):
        os.system("mkdir csvs")        
    with sqlite3.connect('results.db') as connection:
        for t in ["tcas", "CPackIPAs"]:
            m, mn = "time", "Time (s)"
            df = pd.read_sql('select program_id as "Program ID", fault_loc_method as "Fault Localization Method", {m} as "{mn}" from (select program_id, fault_loc_method, time from {tb} where state = "SUCCESS" and time < {t} union select program_id, fault_loc_method, {t}+100 as time from {tb} where time >= {t} or state != "SUCCESS");'.format(m=m,mn=mn,t=TIMEOUT,tb=t), connection).reset_index()
            df.to_csv('csvs/fault_loc_{m}.csv'.format(m=m), index=False)
            q = pd.DataFrame(df.set_index(["Fault Localization Method", "Program ID"]))[mn]
            df_u = q.unstack(["Fault Localization Method"])
            print("Generating Cactus plots")
            gen_cactus_plot(df_u, t, m, mn, TIMEOUT, xmin=0 if t == "tcas" else 325)            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # executor.map(gen_scatter_plot, [df_u.loc[:,m] for m in combinations(df_u.columns, 2)])
                executor.map(gen_scatter_plot, [(df_u.loc[:,mi], TIMEOUT, "time", "(s)", 0.5, t) for mi in combinations(df_u.columns, 2)])                

            print("Generating Scatter plots")
            for m, mn, lb, xmin in [("opt_cost", "Optimum Cost", "memout/timeout", 0.5), ("num_diagnoses", "\#Diagnoses", "memout/timeout", 0.5)]:
                max_num = int(max((pd.read_sql('select {m} from {tb} where {m};'.format(m=m,tb=t), connection).reset_index()[m])))
                df = pd.read_sql('select program_id as "Program ID", fault_loc_method as "Fault Localization Method", {m} as "{mn}" from (select program_id, fault_loc_method, {m} from {tb} where state = "SUCCESS" and {m} > -1 and {m} is not NULL and time < {t} union select program_id, fault_loc_method, {ma}+100 as {m} from {tb} where time >= {t} or state != "SUCCESS" or {m} is NULL or {m} = -1);'.format(m=m,mn=mn,ma=max_num,t=TIMEOUT,tb=t), connection).reset_index()
                # df = pd.read_sql('select program_id as "Program ID", fault_loc_method as "Fault Localization Method", {m} as "{mn}" from {tb} where state = "SUCCESS";'.format(m=m,mn=mn,tb=t), connection).reset_index()
                df.to_csv('csvs/{t}_{m}.csv'.format(t=t, m=m), index=False)
                # print(df)                
                q = pd.DataFrame(df.set_index(["Fault Localization Method", "Program ID"]))[mn]
                df_u = q.unstack(["Fault Localization Method"])

                gen_cactus_plot(df_u, t, m, mn, max_num)

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    executor.map(gen_scatter_plot, [(df_u.loc[:,mi], max_num, m, lb, xmin, t) for mi in combinations(df_u.columns, 2)])
    print("All plots have been generated!")
if __name__ == '__main__':
    if len(sys.argv) > 1:
        TIMEOUT = int(sys.argv[1])
    main()
