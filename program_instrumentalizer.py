#!/usr/bin/python
#Title			: program_instrumentalizer.py
#Usage			: python program_instrumentalizer.py -h
#Author			: pmorvalho
#Date			: May 22, 2023
#Description		: Instrumentalizes each program instruction or expression.
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2023 Pedro Orvalho.
#==============================================================================

from __future__ import print_function
import argparse
from sys import argv
import sys, os
import re
from copy import deepcopy
import argparse
from sys import argv
from shutil import copyfile
from itertools import product
from numpy import binary_repr
import pickle
import gzip
import pathlib
import random
import glob

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator

from helper import *

from program_unroller import *

LVAR="__l_"

def get_bool_vars_decls(bool_vars, coord, loop_vars=None, else_vars=None, second_step_vars=None):
    decls = []
    seen = []
    if loop_vars != None:
        for v in loop_vars:
            if v in seen:
                continue
            t,d = bool_vars[v]
            decls.append(c_ast.Decl(v, [], [], [], [],                          
                                   c_ast.TypeDecl(v,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType([t], coord=coord),
                                                  coord=coord),
                                   None,
                                   None,
                                   coord=coord))
            seen.append(v)
    if else_vars != None:
        for v in else_vars:
            if v in seen:
                continue
            t,d = bool_vars[v]
            decls.append(c_ast.Decl(v, [], [], [], [],                          
                                   c_ast.TypeDecl(v,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType([t], coord=coord),
                                                  coord=coord),
                                   None,
                                   None,
                                   coord=coord))
            seen.append(v)
    else:
        for i, (t, d) in bool_vars.items():
            # if "__e_" in i:
            if LVAR not in i:
                continue
            j = i
            if "[" in i:
                j = i.split("[")[0]
            if second_step_vars and j not in second_step_vars.keys():
                if d <= 1:
                    decls.append(c_ast.Decl(i, [], [], [], [],                          
                                   c_ast.TypeDecl(i,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType(["bool"], coord=coord),
                                                  coord=coord),                                        
                                    c_ast.Constant(type='bool', value='true') if d == 0 else c_ast.InitList([c_ast.Constant(type='bool', value='true') for _ in range(args.num_unroll)], coord),
                                   None,
                                   coord=coord))
                elif d == 2:
                    decls.append(c_ast.Decl(i, [], [], [], [],                          
                                   c_ast.TypeDecl(i,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType([t], coord=coord),
                                                  coord=coord),
                                    # c_ast.InitList([c_ast.InitList([c_ast.Constant(type='bool', value='true', coord=coord)], coord)], coord),
                                   # c_ast.InitList([c_ast.Constant(type='bool', value='true') for _ in range(args.num_unroll)], coord),
                                   c_ast.InitList([c_ast.InitList([c_ast.Constant(type='bool', value='true') for _ in range(args.num_unroll)], coord) for _ in range(args.num_unroll)], coord),                                   
                                   None,
                                   coord=coord))
                else:
                    decls.append(c_ast.Decl(i, [], [], [], [],                          
                                   c_ast.TypeDecl(i,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType([t], coord=coord),
                                                  coord=coord),
                                   c_ast.InitList([c_ast.InitList([c_ast.Constant(type='bool', value='true') for _ in range(args.num_unroll)], coord) for _ in range(args.num_unroll)], coord),                                   
                                   None,
                                   coord=coord))
                    
            else:
                decls.append(c_ast.Decl(i, [], [], [], [],                          
                                   c_ast.TypeDecl(i,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType([t], coord=coord),
                                                  coord=coord),
                                   None,
                                   None,
                                   coord=coord))
                if second_step_vars and j in second_step_vars.keys() and d > 0:
                    for u in range(args.num_unroll):
                        if u not in second_step_vars[j]:
                            decls.append(c_ast.Assignment('=', c_ast.ArrayRef(c_ast.ID(j, coord), c_ast.Constant(type='int', value=str(u), coord=coord),coord), c_ast.Constant(type='bool', value='true', coord=coord), coord))                        
    return decls
        
# def generate_empty_functions():
#     # Function definition for nondet_int
#     nondet_int_func = c_ast.FuncDecl(args=None,
#                           type=c_ast.TypeDecl(
#                               declname='nondet_int',
#                               quals=[],
#                               align=None,            
#                               type=c_ast.IdentifierType(['int'])
#                           ))

#     # Function definition for nondet_char
#     nondet_char_func = c_ast.FuncDecl(args=None,
#                               type=c_ast.TypeDecl(
#                                   declname='nondet_char',
#                                   quals=[],
#                                   align=None,            
#                                   type=c_ast.IdentifierType(['char'])))
                       

#     # Function declaration for nondet_float
#     nondet_float_func = c_ast.FuncDecl(
#         args=None,
#         type=c_ast.TypeDecl(
#             declname='nondet_float',
#             quals=[],
#             align=None,
#             type=c_ast.IdentifierType(['float'])
#         )
#     )

#     # Function declaration for nondet_bool
#     nondet_bool_func = c_ast.FuncDecl(
#         args=None,
#         type=c_ast.TypeDecl(
#             declname='nondet_bool',
#             quals=[],
#             align=None,
#             type=c_ast.IdentifierType(['bool'])
#         )
#     )
    
#     return [nondet_int_func, nondet_char_func, nondet_float_func, nondet_bool_func]

#-----------------------------------------------------------------

class ProgramInstrumentalizerVisitor(ASTVisitor):

    def __init__ (self, num_unroll=3, second_step_vars=None, bug_assist=False):
        super().__init__()
        self.bool_vars = dict()
        self.else_vars = list()
        # counter for boolean variables
        self.bool_cnt = 0
        self.max_bool_cnt = 0
        # current loop depth
        self.var_initialization = None
        self.loop_cnt = 0
        self.loop_offset_inc = list()
        self.loop_depth = 0
        self.loop_offset = list()
        # to keep track of function calls and their relaxation variables
        self.inside_func_call = False
        self.funcall_name = None
        self.funcall_offset = dict()
        self.functions_bvars_2_coord = dict()
        # list with the program variables
        self.scope_vars = dict()
        # flag to use while checking an if-statement
        self.check_simple_if_else = False
        # dict with infromations about the variables declared inside each scope
        self.blocks_vars = dict()
        # flag to know if we are inside a variable declaration
        self.declaring_var = False
        # variable to know the name of the current variable being declared
        self.curr_var = None
        # number of unrolls for the loops
        self.max_offset = num_unroll
        # # mapping to the original program statemets
        self.map_stu_stmts = dict()
        # flag for counting the number of relaxation vars, if turned off the visitor relaxes the program
        self.count_relax_vars = False
        # a mapping from functions' names to the number of relaxation variables needed in those functions
        self.relax_vars_per_function = dict({"printInt" : [], "printChar" : [], "printChars" : [], "printFloat" : [], "nondet_int" : [], "nondet_bool" : [], "nondet_float" : [], "nondet_char" : []})
        # flag to indicate that the visitor encountered a function with missing info
        self.missing_func_def = None
        # to keep track of the number of boolean variables (relaxation vars) needed for the current function
        self.bvs = list()
        # to know the current function name (needed for recursive functions)
        self.curr_func_name = None
        # loop_vars to declare when not in main
        self.offsets_to_declare = list()
        # to know when we are visiting the top binary op of a if-condition
        self.if_cond = False
        self.else_stmt = False
        # to create the mappings between relaxation variables and their lines of code
        self.map_bool_vars = False
        # to map bool vars (relaxation variables) between functions
        self.map_bool_vars_among_funcs = dict()
        # the set of relaxation variables (of the main function) that need to be more relaxed during the second step of instrumentalization
        self.MCSes = bug_assist
        self.second_step_vars = None
        if second_step_vars:
            self.second_step_vars = dict()
            index = args.fault_index
            for k in second_step_vars.keys():
                # for l in second_step_vars[k]:
                #     self.second_step_vars += list(l["lines"].keys())
                try:
                    if isinstance(second_step_vars[k], list):
                        for l in second_step_vars[k][index]["lines"].keys():
                            for s in second_step_vars[k][index]["lines"][l]:
                                if l not in self.second_step_vars.keys():
                                    self.second_step_vars[l] = [s[1]]
                                else:
                                    self.second_step_vars[l].append(s[1])
                    elif self.MCSes:
                        if len(second_step_vars[k]["top_choice"]) > index:
                            for s in second_step_vars[k]["top_choice"][index][1]:
                                if s[0] not in self.second_step_vars.keys():
                                    self.second_step_vars[s[0]] = [s[1]]
                                else:
                                    self.second_step_vars[s[0]].append(s[1])
                        elif index > 0:
                            exit("No more faults to relax!")
                    else:
                        self.MCSes=True
                        if len(second_step_vars[k]["top_choice"]) > index:
                            for s in second_step_vars[k]["top_choice"][index]["key"]:
                                if s[0] not in self.second_step_vars.keys():
                                    self.second_step_vars[s[0]] = [s[1]]
                                else:
                                    self.second_step_vars[s[0]].append(s[1])
                        elif index > 0:
                            exit("No more faults to relax!")
                except:
                    exit("No more faults to relax!")

            if args.verbose:
                print("Second step variables to relax more and introduce nondeterministic values:", self.second_step_vars)

        # self.second_step_vars = ["__l_63__"]

        # bvar on hold. To know which relaxation var we should use next.
        self.bvar_on_hold = None
        self.arg_cnt = 0 


    def get_next_bool_var(self, t="bool",  else_var=False, arg_var = False, depth=0, func_decl=False, func_call=False, inside_main=False, coord=None):
        cnt = 0
        if not arg_var:
            self.bool_cnt += 1
            cnt = self.bool_cnt
        else:
            self.arg_cnt += 1
            cnt = self.arg_cnt
            
        self.max_bool_cnt = max(self.max_bool_cnt, self.bool_cnt) if self.curr_func_name == "main" else self.max_bool_cnt
        if depth == 0:
            b_var = "__{l}_{b}__".format(l="l" if not arg_var else "a", b=cnt) if not else_var else "__e_{b}__".format(b=cnt)
            if b_var not in self.bool_vars.keys() and inside_main:
                self.bool_vars[b_var] = (t, depth)
                if else_var:
                    self.else_vars.append(b_var)
            elif inside_main and self.bool_vars[b_var] != (t, depth):
                b_var = self.get_next_bool_var(t, depth, decl, main, coord, arg_var=arg_var)            
        else:
            b_var = "__{l}_{b}__".format(l="l" if not arg_var else "a", b=cnt) if not else_var else "__e_{b}__".format(b=cnt)
            decl_b_var = "__{l}_{b}__".format(l="l" if not arg_var else "a", b=cnt) if not else_var else "__e_{b}__".format(b=cnt)
            for d in range(depth):
                if (not func_decl and not func_call) or (d < self.loop_depth):
                    b_var += "[{v_os}]".format(v_os=self.loop_offset[d])
                decl_b_var += "[{nu}]".format(nu=self.max_offset)
            if decl_b_var not in self.bool_vars.keys() and inside_main:
                self.bool_vars[decl_b_var] = (t, depth)
                if else_var:
                    self.else_vars.append(decl_b_var)
            elif inside_main and self.bool_vars[decl_b_var] != (t, depth):
                b_var = self.get_next_bool_var(t, depth, decl, main, coord, arg_var=arg_var)
                
            if func_decl:
                return decl_b_var
            if func_call:
                if self.curr_func_name == "main":
                    self.map_stu_stmts[b_var] = self.functions_bvars_2_coord[self.funcall_name][self.funcall_offset[self.funcall_name]]
                self.funcall_offset[self.funcall_name] += 1
                return b_var

        if func_call:
            if self.curr_func_name == "main":
                self.map_stu_stmts[b_var] = self.functions_bvars_2_coord[self.funcall_name][self.funcall_offset[self.funcall_name]]
            self.funcall_offset[self.funcall_name] += 1            
        elif not func_decl and self.curr_func_name == "main":
            self.map_stu_stmts[b_var] = (int(str(coord).split(":")[1]), (self.curr_func_name, self.bool_cnt))
        
        return b_var

    def get_next_loop_offset_var(self, coord):
        self.loop_depth += 1
        self.loop_cnt += 1        
        l_var = "__loop_offset_{b}__".format(b=self.loop_cnt)
        if l_var not in self.bool_vars.keys():            
            self.bool_vars[l_var] = ("int", 0)
        self.loop_offset.append(l_var)
        #  the idea is to put False when we want the increment to be put at the end of the current block
        self.loop_offset_inc.append(c_ast.UnaryOp("p++", c_ast.ID(l_var, coord), coord))
        # if self.curr_func_name != "main":
        self.offsets_to_declare.append(l_var)

    def get_node_type(self, node):
        if isinstance(node, c_ast.ID):
            t = self.scope_vars[node.name]
        elif isinstance(node, c_ast.Assignment):
            t = self.get_node_type(node.lvalue)
        elif isinstance(node, c_ast.FuncCall):
            t = self.get_node_type(node.name)
        elif isinstance(node, c_ast.ArrayRef):
            t = self.get_node_type(node.name)
        elif isinstance(node, c_ast.StructRef):
            t = self.get_node_type(node.name)
        elif isinstance(node, c_ast.PtrDecl):
            t = self.get_node_type(node.type)
        elif isinstance(node, c_ast.TypeDecl):
            t = self.get_node_type(node.declname)
        elif isinstance(node, c_ast.Decl):
            t = self.get_node_type(node.name)
        elif isinstance(node, c_ast.Struct):
            t = self.get_node_type(node.name)
        elif isinstance(node, c_ast.Union):
            t = self.get_node_type(node.name)
        elif isinstance(node, c_ast.Enum):
            t = self.get_node_type(node.name)
        # elif isinstance(node, c_ast.Typename):
        #     t = self.get_node_type(node.type)
        # elif isinstance(node, c_ast.Pragma):
        #     t = self.get_node_type(node.string)
        elif isinstance(node, c_ast.Constant):
            t = node.type  # Return the value of the constant
        if "array-" in t:
            t = t.replace("array-", "")
        return t

    def introduce_nondet(self, var):
        if not self.second_step_vars or self.MCSes:
            return False
        if var in self.second_step_vars.keys():
            return True
        for v in self.second_step_vars.keys():
            if v in var:
                return True
        return False
    
    def exit_loop(self, coord):
        self.loop_depth -= 1
        #  the idea is to put True when we want the assignment right before the current loop
        self.var_initialization = c_ast.Assignment('=', c_ast.ID(self.loop_offset[-1], coord), c_ast.Constant("int", "0", coord), coord)
        self.loop_offset.pop()

    def sensitive_functions(self, x):
        return (isinstance(x, c_ast.FuncCall) and x.name.name == "assert") or (isinstance(x, c_ast.Assignment) and (isinstance(x.rvalue, c_ast.FuncCall) and x.rvalue.name.name == "print"))
    
    def relax_node(self, x):
        return not isinstance(x, c_ast.If) and not isinstance(x, c_ast.While) and not isinstance(x, c_ast.For) and not isinstance(x, c_ast.DoWhile) and not isinstance(x, c_ast.Compound) and not isinstance(x, c_ast.Return) and not self.sensitive_functions(x)

    def find_relax_vars(self, func_defs):
        for j in range(len(func_defs)):
            f = func_defs[j]
            f_name = f.decl.type.type.declname
            
            if f_name in self.relax_vars_per_function.keys() and self.relax_vars_per_function[f_name] != None:
                continue
            # cleaning up
            self.missing_func_def = None
            self.bvs = list()
            self.visit(f)
            n, v = self.bvs, self.missing_func_def
            if v != None:
                if args.verbose:
                    print("While processing function", f_name, " found missing info on function", v)
                for i in range(j+1,len(func_defs)):
                    f2 = func_defs[i]
                    t = f2.decl.type.type.declname
                    if v == t:
                        func_defs.pop(i)
                        func_defs = [f2]+func_defs                         
                        return self.find_relax_vars(func_defs)
            elif n != None:
                self.relax_vars_per_function[f_name] = n
                
            self.bvs = list()                                       
            self.missing_func_def = None
            
    def visit(self, node):
        #node.show()
        return c_ast.NodeVisitor.visit(self, node)

    def visit_FileAST(self, node):
        #print('****************** Found FileAST Node *******************')
        n_ext = []
        fakestart_pos = -1 #for the case of our injected function which do not have the fakestart function in their ast
        self.count_relax_vars = True
        func_defs=list()
        main_f = None
        for e in range(len(node.ext)):
            x = node.ext[e]
            n_ext.append(self.visit(x))
            if fakestart_pos==-1 and isinstance(x, c_ast.FuncDef) and "fakestart" in x.decl.type.type.declname:
                fakestart_pos=e
                
            if isinstance(x, c_ast.FuncDef) and x.decl.type.type.declname != "main":
                func_defs.append(x)
            if isinstance(x, c_ast.FuncDef) and x.decl.type.type.declname == "main":
                main_f = x
        self.find_relax_vars(func_defs)
        if args.verbose:
            print("Relaxation vars per function:")
            print(self.relax_vars_per_function)

        self.map_bool_vars = True
        for j in range(len(func_defs)):
            f = func_defs[j]
            f_name = f.decl.type.type.declname
            self.visit(f)

        self.visit(main_f)

        self.map_bool_vars = False
        self.count_relax_vars = False        
        if args.verbose:
            print("Instrumentalizing...")
            
        # if self.second_step_vars:
        #     # inject function that generates non-deterministic values
        #     # moved these functions to prints.c        
        #     # n_ext = [c_ast.FuncDef(), ]
        #     n_ext = generate_empty_functions()
        # else:
        #     n_ext = []
        n_ext = []                    
        for e in range(len(node.ext)):
            x = node.ext[e]
            n_ext.append(self.visit(x))
            self.bool_cnt = 0
            self.loop_cnt = 0
            
        n_file_ast = c_ast.FileAST(n_ext[fakestart_pos+1:])
        if args.verbose:
            print("Mapping between relaxation vars and program_lines:")
            print(self.map_stu_stmts)
        return n_file_ast

    def visit_Decl(self, node):
        # print('****************** Found Decl Node *******************')
        if not isinstance(node.type, c_ast.TypeDecl):
            # because it can be other type of declaration. Like func declarations.
            node.type = self.visit(node.type)
            if isinstance(node.type, c_ast.Enum):
                # Enum are declared in the var_info.h file!
                return node
            elif isinstance(node.type, c_ast.PtrDecl):
                self.scope_vars[node.type.type.declname] = node.type.type.type.names[0]
                return node                    
            elif isinstance(node.type, c_ast.ArrayDecl):
                return node
        # node.show()
        type = node.type
        if isinstance(type.type, c_ast.Enum):
             # type = type.type.name            # node.type = self.visit(node.type)
            type = node.type.type
        else:
            type = node.type
            while not isinstance(type, c_ast.IdentifierType):
                type = type.type
                if isinstance(type, c_ast.TypeDecl):
                    declname = type.declname
            type = type.names[0]
        
        self.scope_vars[node.name] = type
        self.curr_var = node.name        
        if node.init != None:
            node.init = self.visit(node.init)            
            
        self.curr_var = None

        return node

    def visit_ArrayDecl(self, node):
        #print('****************** Found Decl Node *******************')
        if isinstance(node.type, c_ast.TypeDecl):
            self.scope_vars[node.type.declname] = "array-"+node.type.type.names[0]
            self.curr_var = node.type.declname

        return node
    
    def visit_Assignment(self, node):
        # print('****************** Found Assignment Node *******************')
        bvar_on_hold = self.bvar_on_hold
        self.bvar_on_hold = None
        if not isinstance(node.rvalue, c_ast.ArrayRef):
            node.rvalue = self.visit(node.rvalue)
        node.lvalue = self.visit(node.lvalue)
        if bvar_on_hold:
            var_name = node.lvalue.name if isinstance(node.lvalue, c_ast.ID) else node.lvalue.name.name if not isinstance(node.lvalue, c_ast.UnaryOp) else node.lvalue.expr.name
            var_name = var_name if var_name in self.scope_vars.keys() else var_name.split("__")[0]
            t = self.scope_vars[var_name]
            if "array-" in t:
                t = t.replace("array-", "")
                # t += "_star"
            node.rvalue = c_ast.TernaryOp(c_ast.ID(bvar_on_hold, node.coord), node.rvalue, c_ast.FuncCall(name=c_ast.ID(name='nondet_'+t, coord=node.coord), args=None, coord=node.coord), coord=node.coord)
        return node

    def visit_ID(self, node):
        # print('****************** Found ID Node *******************')
        return node

    def visit_Enum(self, node):
        # #print('****************** Found Enum Node *******************')
        # insert each enum on the .h file, after the scope functions of the fakestart function
        return node

    def visit_UnaryOp(self, node):
        #print('****************** Found Unary Operation *******************')
        node.expr = self.visit(node.expr)
        return node
        # b_var = self.get_next_bool_var(depth=self.loop_depth, coord=node.coord)        
        # node.expr = self.visit(node.expr)
        # return c_ast.TernaryOp(c_ast.ID(b_var, node.coord), node, c_ast.Constant("int", "1", node.coord), node.coord)
    
    def visit_BinaryOp(self, node):
        # print('****************** Found Binary Operation *******************', node.coord)
        # print(node.show())
        if_cond = self.if_cond
        else_stmt = self.else_stmt
        self.if_cond = False
        self.else_stmt = False
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.op not in arith_bin_ops and if_cond:
            if self.map_bool_vars:
                self.functions_bvars_2_coord[self.curr_func_name] += [(int(str(node.coord).split(":")[1]), (self.curr_func_name,len(self.functions_bvars_2_coord[self.curr_func_name])))]
            elif self.count_relax_vars:
                self.bvs += [(self.loop_depth,False,self.curr_func_name,len(self.bvs))]
            if else_stmt:                
                if self.map_bool_vars:
                    self.functions_bvars_2_coord[self.curr_func_name] += [(int(str(node.coord).split(":")[1]), (self.curr_func_name,len(self.functions_bvars_2_coord[self.curr_func_name])))]
                elif self.count_relax_vars:
                    self.bvs += [(self.loop_depth,True,self.curr_func_name,len(self.bvs))]                    
        if node.op in arith_bin_ops or self.count_relax_vars or not if_cond:
            return c_ast.BinaryOp(node.op, left, right, node.coord)
        b_var = self.get_next_bool_var(depth=self.loop_depth, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord)
        if not else_stmt:
            if self.second_step_vars and self.introduce_nondet(b_var):
                return c_ast.TernaryOp(c_ast.ID(b_var, node.coord), c_ast.BinaryOp(node.op, left, right, node.coord), c_ast.FuncCall(name=c_ast.ID(name='nondet_bool', coord=node.coord), args=None, coord=node.coord), node.coord)
            return c_ast.BinaryOp('||', c_ast.UnaryOp('!', c_ast.ID(b_var, node.coord), node.coord), c_ast.BinaryOp(node.op, left, right, node.coord), node.coord)
        else:
            e_var = self.get_next_bool_var(depth=self.loop_depth, else_var = True, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord)            
            return c_ast.TernaryOp(c_ast.UnaryOp('!', c_ast.ID(b_var, node.coord), node.coord),  c_ast.UnaryOp('!', c_ast.ID(e_var, node.coord), node.coord), c_ast.BinaryOp(node.op, left, right, node.coord), node.coord)

    def visit_TernaryOp(self, node):
        # print('****************** Found Ternary Op Node *******************')
        self.if_cond = True
        self.else_stmt = True
        if isinstance(node.cond, c_ast.ID) and LVAR not in node.cond.name:
            node.cond = c_ast.BinaryOp('!=', node.cond, c_ast.Constant("int", str(0), node.coord), node.cond.coord)
        n_cond = self.visit(node.cond)
        self.if_cond = False
        self.else_stmt = False
        n_iftrue = self.visit(node.iftrue)
        n_iffalse = node.iffalse
        # if there exists and else statement
        if n_iffalse is not None:
            n_iffalse = self.visit(n_iffalse)
        #print('****************** New Cond Node *******************')
        n_ternary =  c_ast.TernaryOp(n_cond, n_iftrue, n_iffalse, node.coord)
        return n_ternary

    def visit_FuncDecl(self, node):
        # print('****************** Found FuncDecl Node *******************')
        fname = node.type.declname
        if "main" != fname and "fakestart" != fname: #ignore main function
            if not self.count_relax_vars and fname in self.relax_vars_per_function.keys():
                bvs=[]
                self.map_bool_vars_among_funcs[fname][fname] = list()
                offset = 0
                for i in self.relax_vars_per_function[fname]:
                    d, t, fn, ind = i
                    l, (fn, ind) = self.functions_bvars_2_coord[fname][offset]
                    if fn not in self.map_bool_vars_among_funcs[fname].keys():
                        self.map_bool_vars_among_funcs[fname][fn] = list()
                    if len(self.map_bool_vars_among_funcs[fname][fn]) > ind:
                        bv = c_ast.ID(self.map_bool_vars_among_funcs[fname][fn][ind], coord=node.coord)
                    else:
                        bv = c_ast.ID(self.get_next_bool_var(depth=self.loop_depth+d, else_var=t, func_call=True, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord), coord=node.coord)
                    offset += 1
                    if bv.name not in self.map_bool_vars_among_funcs[fname][fname]:
                        bvs.append(c_ast.Decl(bv, [], [], [], [],                            
                                   c_ast.TypeDecl(bv.name,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType(["bool"], coord=node.coord),
                                                  coord=node.coord),
                                   None,
                                   None,
                                   coord=node.coord))
                    self.map_bool_vars_among_funcs[fname][fn].append(bv.name)
                    if fn != fname:
                        self.map_bool_vars_among_funcs[fname][fname].append(bv.name)
                    
                if node.args:
                    node.args.params += bvs
                else:
                    node.args = c_ast.ParamList(bvs, coord=node.coord)
        node.args = self.visit(node.args)
        node.type = self.visit(node.type)
        return node
        
    def visit_FuncDef(self, node):
        #print('****************** Found FuncDef Node *******************')
        decl = node.decl
        if node.decl.type and node.decl.type.args:
            node.decl.type.args = self.visit(node.decl.type.args)
        param_decls = self.visit(node.param_decls)
        fname = node.decl.type.type.declname
        self.curr_func_name = fname
        if fname not in  self.functions_bvars_2_coord.keys():
            self.functions_bvars_2_coord[fname] = list()
            
        self.offsets_to_declare = list()

        if not self.map_bool_vars:
            self.map_bool_vars_among_funcs[self.curr_func_name] = dict()
        
        if "main" != fname and "fakestart" != fname: #ignore main function
            if not self.count_relax_vars and fname in self.relax_vars_per_function.keys():
                bvs=[]
                self.map_bool_vars_among_funcs[self.curr_func_name][fname] = list()
                offset = 0
                for i in self.relax_vars_per_function[fname]:
                    d, t, fn, ind = i
                    l, (fn, ind) = self.functions_bvars_2_coord[self.curr_func_name][offset]
                    if fn not in self.map_bool_vars_among_funcs[self.curr_func_name].keys():
                        self.map_bool_vars_among_funcs[self.curr_func_name][fn] = list()
                    if len(self.map_bool_vars_among_funcs[self.curr_func_name][fn]) > ind:
                        bv = c_ast.ID(self.map_bool_vars_among_funcs[self.curr_func_name][fn][ind], coord=node.coord)
                    else:
                        bv = c_ast.ID(self.get_next_bool_var(depth=self.loop_depth+d, else_var=t, func_call=True, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord), coord=node.coord)
                    offset += 1
                    if bv.name not in self.map_bool_vars_among_funcs[self.curr_func_name][fname]:
                        bvs.append(c_ast.Decl(bv, [], [], [], [],                            
                                   c_ast.TypeDecl(bv.name,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType(["bool"], coord=node.coord),
                                                  coord=node.coord),
                                   None,
                                   None,
                                   coord=node.coord))
                    self.map_bool_vars_among_funcs[self.curr_func_name][fn].append(bv.name)
                    if fn != fname:
                        self.map_bool_vars_among_funcs[self.curr_func_name][fname].append(bv.name)
                if node.decl.type.args:
                    node.decl.type.args.params += bvs
                else:
                    node.decl.type.args = c_ast.ParamList(bvs, coord=node.coord)

        if not self.map_bool_vars:
            
            self.map_bool_vars_among_funcs[self.curr_func_name] = dict()

        body = node.body
        coord = node.coord
        # self.first_check = True
        # self.first_check = False
        self.bool_cnt = 0
        self.loop_cnt = 0
        blocks=[]
        if fname == "main" and not self.count_relax_vars:
            for pi in body.block_items:
                self.bool_cnt = 0
                self.loop_cnt = 0
                pi_visited = self.visit(pi)
                if isinstance(pi_visited, c_ast.Label) and isinstance(pi_visited.stmt, c_ast.Compound):
                    pi_visited.stmt.block_items = get_bool_vars_decls(self.bool_vars, node.coord, else_vars=self.else_vars) + pi_visited.stmt.block_items
                blocks.append(pi_visited)
                
            blocks = get_bool_vars_decls(self.bool_vars, node.coord, loop_vars=self.offsets_to_declare, second_step_vars=self.second_step_vars) + blocks
        else:
            body = self.visit(body)
            # blocks = get_bool_vars_decls(self.bool_vars, node.coord, loop_vars=self.offsets_to_declare) + body.block_items
            blocks = body.block_items            
            
        main_block = c_ast.Compound(blocks, coord)
        n_func_def_ast = c_ast.FuncDef(decl, param_decls,main_block, coord)
        self.curr_func_name = None
        return n_func_def_ast

    def visit_FuncCall(self, node):
        # print('****************** Found FuncCall Node *******************')
        self.inside_func_call = True
        fname = node.name.name        
        self.funcall_name = fname
        self.funcall_offset[self.funcall_name] = 0
        if fname != "assert":
            if fname not in self.relax_vars_per_function.keys() and fname != self.curr_func_name:
                self.missing_func_def = fname
            elif fname == self.curr_func_name:
                old_cnt = self.bool_cnt
                self.bool_cnt = 0
            elif self.count_relax_vars and not self.map_bool_vars:
                self.map_bool_vars_among_funcs[self.curr_func_name][fname] = list()
                for i in self.relax_vars_per_function[fname]:
                    d, t, fn, ind = i
                    new_t = (self.loop_depth+d, t, fn, ind)
                    if new_t not in self.bvs:
                        self.bvs += [new_t]
                
            if self.map_bool_vars and fname in self.relax_vars_per_function.keys():
                if self.funcall_name not in self.map_bool_vars_among_funcs[self.curr_func_name].keys() or self.funcall_name not in self.map_bool_vars_among_funcs[self.curr_func_name][fname] == list():
                    self.funcall_offset[self.funcall_name] = 0
                    for i in self.relax_vars_per_function[fname]:
                        bv = self.functions_bvars_2_coord[self.funcall_name][self.funcall_offset[self.funcall_name]]
                        if bv not in self.functions_bvars_2_coord[self.curr_func_name]:
                            self.functions_bvars_2_coord[self.curr_func_name] += [bv]
                        self.funcall_offset[self.funcall_name] += 1
                            
            if not self.count_relax_vars and fname in self.relax_vars_per_function.keys():
                bvs=[]
                if fname not in self.map_bool_vars_among_funcs[self.curr_func_name].keys():
                    self.map_bool_vars_among_funcs[self.curr_func_name][fname] = list()
                    offset = 0
                    for i in self.relax_vars_per_function[fname]:
                        d, t, fn, ind = i
                        l, (fn, ind) = self.functions_bvars_2_coord[self.funcall_name][offset]
                        if fn not in self.map_bool_vars_among_funcs[self.curr_func_name].keys():
                            self.map_bool_vars_among_funcs[self.curr_func_name][fn] = list()
                        if len(self.map_bool_vars_among_funcs[self.curr_func_name][fn]) > ind:
                            lvar = self.map_bool_vars_among_funcs[self.curr_func_name][fn][ind]
                            if lvar not in bvs:
                                bvs.append(lvar)
                        else:                            
                            bvs.append(c_ast.ID(self.get_next_bool_var(depth=self.loop_depth+d, else_var=t, func_call=True, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord), coord=node.coord))
                            self.map_bool_vars_among_funcs[self.curr_func_name][fn].append(bvs[-1])
                        offset += 1
                    self.map_bool_vars_among_funcs[self.curr_func_name][fname] = bvs
                else:
                    bvs = self.map_bool_vars_among_funcs[self.curr_func_name][fname]
                if node.args:
                    node.args.exprs += bvs
                else:
                    node.args = c_ast.ExprList(bvs, coord=node.coord)            
            node.args = self.visit(node.args)

            if fname == self.curr_func_name:
                self.bool_cnt = old_cnt
                
        self.inside_func_call = False
        self.funcall_name = None
        self.funcall_offset[self.funcall_name] = 0
        self.bvar_on_hold = None
        return c_ast.FuncCall(node.name, node.args, node.coord)

    def visit_ExprList(self, node):
        # print('****************** Found ExprList Node *******************')
        for e in range(len(node.exprs)):
            if not node.exprs[e]:
                if len(node.exprs) == 1:
                    node.exprs = []
                    return node
                continue
            if self.count_relax_vars and not self.map_bool_vars:
                if not self.inside_func_call:
                    self.bvs += [(self.loop_depth,False,self.curr_func_name,len(self.bvs))]
            elif self.map_bool_vars and not self.inside_func_call:
                self.functions_bvars_2_coord[self.curr_func_name] += [(int(str(node.exprs[e].coord).split(":")[1]), (self.curr_func_name,len(self.functions_bvars_2_coord[self.curr_func_name])))]
            elif not self.inside_func_call:
                b_var = self.get_next_bool_var(depth=self.loop_depth, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord)
                if not self.second_step_vars or (self.second_step_vars and not self.introduce_nondet(b_var)) or not isinstance(node.exprs[e], c_ast.Assignment):
                    node.exprs[e] = self.visit(c_ast.TernaryOp(c_ast.ID(b_var, node.coord), node.exprs[e], c_ast.Constant("int", "1", node.coord), node.coord))
                else:
                    self.bvar_on_hold = b_var
                    node.exprs[e] = self.visit(node.exprs[e])
            # elif self.inside_func_call and self.second_step_vars and self.introduce_nondet(self.bvar_on_hold):
            #     a_var = self.get_next_bool_var(depth=self.loop_depth, arg_var = True, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord)
            #     t = self.get_node_type(node.exprs[e])
            #     node.exprs[e] = self.visit(c_ast.TernaryOp(c_ast.ID(a_var, node.coord), node.exprs[e], c_ast.FuncCall(name=c_ast.ID(name='nondet_'+t, coord=node.coord), args=None, coord=node.coord), node.coord))
          
            node.exprs[e] = self.visit(node.exprs[e])
        return node
    
    def visit_ParamList(self, node):
        # print('****************** Found ParamList Node *******************')
        for e in range(len(node.params)):
            node.params[e] = self.visit(node.params[e])
        return node
    
    def visit_Compound(self, node):
        #print('****************** Found Compound Node *******************')
        block_items = node.block_items
        coord = node.coord
        n_block_items = []
        if block_items is not None:
            for x in block_items:            
                assert(x != None)
                if isinstance(x, c_ast.Decl):
                    self.declaring_var = True
                    n_block_items.append(self.visit(x))
                elif isinstance(x, c_ast.Continue):
                    if self.count_relax_vars and not self.map_bool_vars:
                        self.bvs += [(self.loop_depth,False,self.curr_func_name,len(self.bvs))]
                        n_block_items.append(self.visit(x))
                    elif self.map_bool_vars:
                        self.functions_bvars_2_coord[self.curr_func_name] += [(int(str(x.coord).split(":")[1]), (self.curr_func_name,len(self.functions_bvars_2_coord[self.curr_func_name])))]
                        n_block_items.append(self.visit(x))
                    else:
                        b_var = self.get_next_bool_var(depth=self.loop_depth, inside_main=True if self.curr_func_name == "main" else False, coord=x.coord)
                        n_block_items.append(c_ast.If(c_ast.ID(b_var, node.coord), c_ast.Compound([self.loop_offset_inc[-1], x], node.coord), None, node.coord))                                                
                elif self.relax_node(x):                
                    if self.count_relax_vars and not self.map_bool_vars:
                        self.bvs += [(self.loop_depth,False,self.curr_func_name,len(self.bvs))]
                        n_block_items.append(self.visit(x))
                    elif self.map_bool_vars:
                        self.functions_bvars_2_coord[self.curr_func_name] += [(int(str(x.coord).split(":")[1]), (self.curr_func_name,len(self.functions_bvars_2_coord[self.curr_func_name])))]
                        n_block_items.append(self.visit(x))
                    else:
                        b_var = self.get_next_bool_var(depth=self.loop_depth, inside_main=True if self.curr_func_name == "main" else False, coord=x.coord)
                        if (not isinstance(x, c_ast.Assignment) and not isinstance(x, c_ast.FuncCall)) or (not self.second_step_vars) or (self.second_step_vars and not self.introduce_nondet(b_var)):
                            n_block_items.append(c_ast.If(c_ast.ID(b_var, node.coord), self.visit(x), None, node.coord))
                        else:
                            self.bvar_on_hold = b_var
                            x = self.visit(x)
                            n_block_items.append(x)                                            
                else:
                    n_block_items.append(self.visit(x))
                    if self.var_initialization is not None:
                        n_block_items.insert(-1, self.var_initialization)
                        self.var_initialization = None

            if self.var_initialization != None:
                n_block_items.append(self.var_initialization)
                self.var_initialization = None
            self.declaring_var = False

        n_compound_ast = c_ast.Compound(n_block_items, node.coord)
        return n_compound_ast

    def visit_If(self, node):
        #print('****************** Found IF Node *******************')
        if not isinstance(node.cond, c_ast.ID):
            self.if_cond = True
            # if node.iffalse:
            self.else_stmt = True
        if isinstance(node.cond, c_ast.ID) and LVAR not in node.cond.name:
            self.if_cond = True
            if node.iffalse:
                self.else_stmt = True
            node.cond = c_ast.BinaryOp('!=', node.cond, c_ast.Constant("int", str(0), node.coord), node.cond.coord)
        n_cond = self.visit(node.cond)
        self.if_cond = False
        self.else_stmt = False
        if isinstance(node.iftrue, c_ast.Compound):
            n_iftrue = self.visit(node.iftrue)
        else:
            n_iftrue = self.visit(c_ast.Compound([node.iftrue], node.iftrue.coord))
        if self.check_simple_if_else:
            self.check_simple_if_else = False
        else:
            self.check_simple_if_else = True

        if node.iffalse is not None and not isinstance(node.iffalse, c_ast.Compound):
            node.iffalse = c_ast.Compound([node.iffalse], node.iffalse.coord)
        n_iffalse = self.visit(node.iffalse)
        # if is just an if without and else or if we already saved the id of the node we can turn off the flag. 
        self.check_simple_if_else = False
        #print('****************** New Cond Node *******************')
        n_if = c_ast.If(n_cond, n_iftrue, n_iffalse, node.coord)
        return n_if

    def visit_For(self, node):
        # print('****************** Found For Node *******************')
        if self.count_relax_vars:
            self.visit(node.init)
            self.loop_depth += 1
            self.visit(node.cond)
            self.visit(node.stmt)
            self.loop_depth -= 1                                               
            self.visit(node.next)
            return node
        n_init = self.visit(node.init)
        self.get_next_loop_offset_var(node.coord)
        if node.cond:
            self.if_cond = True
            n_cond = self.visit(node.cond)
            self.if_cond = False
        n_stmt = self.visit(node.stmt)
        n_next = self.visit(node.next)
        if isinstance(n_next, c_ast.ExprList):
            n_next.exprs.append(self.loop_offset_inc[-1])
        else:
            n_next = c_ast.ExprList([n_next, self.loop_offset_inc[-1]], node.coord)            
        self.loop_offset_inc.pop()  
        # We dont need to put a scope_info at the end of the for because the compound node already does that
        n_for = c_ast.For(n_init, n_cond, n_next, n_stmt, node.coord)
        self.exit_loop(node.coord) 
        return n_for

    def visit_While(self, node):
        #print('****************** Found While Node *******************')
        if self.count_relax_vars:
            self.loop_depth += 1            
            self.visit(node.cond)
            self.visit(node.stmt)
            self.loop_depth -= 1                        
            return node

        self.get_next_loop_offset_var(node.coord)
        if node.cond:
            self.if_cond = True
            n_cond = self.visit(node.cond)
            self.if_cond = False
        n_stmt = self.visit(node.stmt)
        if isinstance(n_stmt, c_ast.Compound):
            n_stmt.block_items.append(self.loop_offset_inc[-1])
        else:
            n_stmt = c_ast.Compound([n_stmt, self.loop_offset_inc[-1]], n_stmt.coord)
        
        self.loop_offset_inc.pop()
        n_while = c_ast.While(n_cond, n_stmt, node.coord)
        self.exit_loop(node.coord)
        return n_while

    def visit_DoWhile(self, node):
        #print('****************** Found While Node *******************')
        if self.count_relax_vars:
            self.loop_depth += 1            
            self.visit(node.stmt)
            self.visit(node.cond)
            self.loop_depth -= 1            
            return node
        
        self.get_next_loop_offset_var(node.coord)
        n_stmt = self.visit(node.stmt)
        if node.cond:
            self.if_cond = True
            n_cond = self.visit(node.cond)
            self.if_cond = False
        if isinstance(n_stmt, c_ast.Compound):
            n_stmt.block_items.append(self.loop_offset_inc[-1])
        else:
            n_stmt = c_ast.Compound([n_stmt, self.loop_offset_inc[-1]], n_stmt.coord)

        self.loop_offset_inc.pop()
        n_while = c_ast.DoWhile(n_cond, n_stmt, node.coord)
        self.exit_loop(node.coord)
        return n_while
    
    def visit_Continue(self, node):
        # print('****************** Found Continue Node *******************')
        return node

    def visit_Label(self, node):
        # print('****************** Found Label Node *******************')        
        node.stmt = self.visit(node.stmt)
        return node

    def visit_Return(self, node):
        # # print('****************** Found Return Node *******************')        
        # if isinstance(node.expr, c_ast.BinaryOp):
        #     if self.count_relax_vars and not self.map_bool_vars:
        #         self.bvs += [(self.loop_depth,False,self.curr_func_name,len(self.bvs))]
        #     elif self.map_bool_vars:
        #         self.functions_bvars_2_coord[self.curr_func_name] += [(int(str(node.coord).split(":")[1]), (self.curr_func_name,len(self.functions_bvars_2_coord[self.curr_func_name])))]
        #     else:
        #         b_var = self.get_next_bool_var(depth=self.loop_depth, inside_main=True if self.curr_func_name == "main" else False, coord=node.coord)
        #         node.expr = c_ast.TernaryOp(c_ast.ID(b_var, node.coord), node.expr, c_ast.UnaryOp("!", node.expr, node.coord), node.coord)
        # else:
        node.expr = self.visit(node.expr)
        return node
    
    def generic_visit(self, node):
        #print('******************  Something else ************')
        return node


class RelaxVarsWeightVisitor(c_ast.NodeVisitor):
    def __init__(self, max_lvars, num_unroll, hierarchical_weights=False):
        self.id_counts = []
        self.lvar_2_weight = dict()
        self.current_function = "global_scope"
        self.lvars_per_function = dict()
        self.missing_info = True
        self.erase_functions = list()
        self.functions_2_ignore = ["assert", "printInt", "printChars", "printFloat", "printChar", "sizeof", "strcmp", "nondet_int", "nondet_bool", "nondet_float", "nondet_char"]
        self.max_lvars = max_lvars
        self.num_unroll = num_unroll
        self.hierarchical_weights = hierarchical_weights
        self.if_cond = False

    def next_iteration(self):
        self.missing_info = False
        for f in set(self.erase_functions):
            del self.lvars_per_function[f]
        self.erase_functions = list()

    def is_another_iteration_needed(self):
        return self.missing_info
    
    def get_weights_map(self):
        return self.lvar_2_weight

    def visit_FuncDef(self, node):
        self.current_function = node.decl.type.type.declname if not isinstance(node.decl.type.type, c_ast.PtrDecl) else node.decl.type.type.type.declname
        self.lvars_per_function[self.current_function] = dict()
        self.generic_visit(node)
        self.current_function = "global_scope"
    
    def visit_FuncCall(self, node):
        funcall_name = node.name.name 
        i = 1 
        if funcall_name in self.lvars_per_function.keys():
            # We should add a try-except in case there is some missing info on inner function calls
            for arg in node.args.exprs:
                if isinstance(arg, c_ast.ID) and LVAR in arg.name:
                    lvar = arg.name
                    fc_lvar = "__l_{i}__".format(i=i)
                    # print(funcall_name, fc_lvar)                    
                    tmp_w = self.lvars_per_function[funcall_name][fc_lvar]
                    if "[" in lvar:
                        lvar = lvar.split("[")[0]
                    self.lvars_per_function[self.current_function][lvar] = tmp_w
                    if self.current_function == "main":
                        self.lvar_2_weight[lvar] = tmp_w if self.hierarchical_weights else 1
                    if args.verbose:
                        print("Current function:", self.current_function, "Relaxation variable:", lvar, "Weight:", tmp_w)                    
                    self.id_counts[-1] += tmp_w
                    i += 1
                elif isinstance(arg, c_ast.ID) and "__e_" in arg.name:
                    i += 1
                else:
                    arg = self.visit(arg)

        elif funcall_name not in self.functions_2_ignore:
            self.missing_info = True
            self.erase_functions.append(self.current_function)
            if args.verbose:
                print("Missing information when calling ", funcall_name)
        else:
            for arg in node.args.exprs:
                # if isinstance(arg, c_ast.FuncCall):
                arg = self.visit(arg)
            if len(self.id_counts) > 0:
                self.id_counts[-1] += self.max_lvars*self.num_unroll
        # self.generic_visit(node)
        return node
    
    def visit_BinaryOp(self, node):        
        if isinstance(node.left, c_ast.UnaryOp) and isinstance(node.left.expr, c_ast.ID) and LVAR in node.left.expr.name:
            lvar = node.left.expr.name
            # if not self.if_cond:
            #     self.id_counts.append(0)
            # self.if_cond = False
            if not self.if_cond:
                self.id_counts.append(0)
            self.if_cond = False
            node.right = self.visit(node.right)
            w = self.id_counts[-1] + 1
            if "[" in lvar:
                lvar = lvar.split("[")[0]
            self.lvars_per_function[self.current_function][lvar] = w                
            if self.current_function == "main":
                self.lvar_2_weight[lvar] = w if self.hierarchical_weights else 1
            self.id_counts.pop()
            if len(self.id_counts) > 0:
                self.id_counts[-1] += w
            if args.verbose:
                print("Current function:", self.current_function, "Relaxation variable:", lvar, "Weight:", w)
        else:
            node.left = self.visit(node.left)            
            node.right = self.visit(node.right)
            
        return node

    def visit_TernaryOp(self, node):
        if isinstance(node.cond, c_ast.UnaryOp) and isinstance(node.cond.expr, c_ast.ID) and LVAR in node.cond.expr.name:
            if isinstance(node.iftrue, c_ast.UnaryOp) and isinstance(node.iftrue.expr, c_ast.ID) and "__e_" in node.iftrue.expr.name:
                lvar = node.cond.expr.name
                # if not self.if_cond:
                #     self.id_counts.append(0)
                # self.if_cond = False
                if_cond = self.if_cond
                if not self.if_cond:
                    self.id_counts.append(0)
                self.if_cond = False
                node.iftrue = self.visit(node.iftrue)                
                node.iffalse = self.visit(node.iffalse)                
                w = self.id_counts[-1] + 1 if not if_cond else self.id_counts[-1]                
                self.id_counts.pop()
                if "[" in lvar:
                    lvar = lvar.split("[")[0]
                self.lvars_per_function[self.current_function][lvar] = w
                if self.current_function == "main":
                    self.lvar_2_weight[lvar] = w if self.hierarchical_weights else 1
                if len(self.id_counts) > 0:
                    self.id_counts[-1] += w                
                if args.verbose: 
                    print("Current function:", self.current_function, "Relaxation variable:", lvar, "Weight:", w)                   
            else:
                lvar = node.cond.expr.name
                self.id_counts.append(0)
                node.iftrue = self.visit(node.iftrue)
                if node.iffalse:
                    node.iffalse = self.visit(node.iffalse)                
                w = self.id_counts[-1] + 1
                if "[" in lvar:
                    lvar = lvar.split("[")[0]
                self.lvars_per_function[self.current_function][lvar] = w
                if self.current_function == "main":
                    self.lvar_2_weight[lvar] = w  if self.hierarchical_weights else 1
                self.id_counts.pop()                
                if len(self.id_counts) > 0:
                    self.id_counts[-1] += w                                
                if args.verbose:
                    print("Current function:", self.current_function, "Relaxation variable:", lvar, "Weight:", w)                                       
        elif isinstance(node.cond, c_ast.ID) and LVAR in node.cond.name:
            lvar = node.cond.name
            self.id_counts.append(0)
            node.iftrue = self.visit(node.iftrue)
            # if node.iffalse:
            #     node.iffalse = self.visit(node.iffalse)                
            w = self.id_counts[-1] + 1
            if "[" in lvar:
                lvar = lvar.split("[")[0]
            self.lvars_per_function[self.current_function][lvar] = w
            if self.current_function == "main":
                self.lvar_2_weight[lvar] = w  if self.hierarchical_weights else 1
            self.id_counts.pop()                
            if len(self.id_counts) > 0:
                self.id_counts[-1] += w                                
            if args.verbose:
                print("Current function:", self.current_function, "Relaxation variable:", lvar, "Weight:", w)            
        else:
            node.cond = self.visit(node.cond)
            node.iftrue = self.visit(node.iftrue)
            if node.iffalse:
                node.iffalse = self.visit(node.iffalse)
            
        return node    

    def visit_If(self, node):
        if isinstance(node.cond, c_ast.ID) and LVAR in node.cond.name:
            # typical relaxation of single instructions
            lvar = node.cond.name
            self.id_counts.append(0)
            node.iftrue = self.visit(node.iftrue)
            w = self.id_counts[-1] + 1
            if "[" in lvar:
                lvar = lvar.split("[")[0]            
            self.lvars_per_function[self.current_function][lvar] = w            
            if self.current_function == "main":
                self.lvar_2_weight[lvar] = w  if self.hierarchical_weights else 1
            self.id_counts.pop()                
            if len(self.id_counts) > 0:
                self.id_counts[-1] += w
            if args.verbose:
                print("Current function:", self.current_function, "Relaxation variable:", lvar, "Weight:", w)                                                           
            if node.iffalse:
                node.iffalse = self.visit(node.iffalse)         
        else:
            if not node.iffalse:
                self.id_counts.append(0)
                node.iftrue = self.visit(node.iftrue)
                self.if_cond = True
                node.cond = self.visit(node.cond)
                self.if_cond = False                
            else:
                node.cond = self.visit(node.cond)
                node.iftrue = self.visit(node.iftrue)
                node.iffalse = self.visit(node.iffalse)
            
        return node
    
# Function to print lines based on coord
def get_complete_map_to_students_statements(coord, map_stu_stmts, num_unroll, last_vars, one_line_functions = None, weights_map = None):
    with open(coord.file, 'r') as file:
        lines = file.readlines()
        n_keys = len(map_stu_stmts.keys())
        n_prints = 0
        new_map = dict()
        for old_k in map_stu_stmts.keys():
            k = old_k.split("[")[0]
            line, f = map_stu_stmts[old_k]
            stmt = lines[line - 1].strip()                
            if k in last_vars or "__e_" in k:
                continue            
            w = 1 if not weights_map else weights_map[k]            
            if args.traces_dir and ("printf" in stmt or "atoi(argv" in stmt or "argc" in stmt):#  or "initialize" in stmt):
                w = None
            elif "printf" in stmt:
                # # Do we need to give more weight to the prints?
                # w = num_unroll*n_keys + 1
                w = 1 if not weights_map else weights_map[k]                
                n_prints += 1
            elif "scanf" in stmt:
                w = n_keys*(num_unroll*n_keys + 1) + 1
                
            new_map[k] =  (line, w, [f"Line {line-1}: {stmt}"])
            if line in one_line_functions.keys():
                for orig_lineno, decl_name in one_line_functions[line]:
                    orig_lineno-=1                    
                    stmt = lines[orig_lineno].strip()
                    new_map[k][-1].append(f"Line {orig_lineno}: {stmt}")

            if args.verbose:
                print(k, new_map[k])
        for v in last_vars[:-1]:
            line, f = map_stu_stmts[v]
            # w = n_prints*(num_unroll*n_keys + 1)+1
            w = n_prints*(num_unroll*n_keys + 1)+(num_unroll*(n_keys-n_prints))+1 if not args.traces_dir else None
            new_map[v] = (line, w, [f"There is a missing '\n' at the end of the output."])
            # new_map[v] = (map_stu_stmts[last_vars[-1]], w, f"There is a missing '\n' at the end of the output.")            
            if args.verbose:
                print(v, new_map[v])

        line, f = map_stu_stmts[last_vars[-1]]
        # w = n_prints*(num_unroll*n_keys + 1)+1
        w = n_prints*(num_unroll*n_keys + 1)+(num_unroll*(n_keys-n_prints))+1 if not args.traces_dir else None
        new_map[last_vars[-1]] = (line, w, [f"The program is only writing a valid perfix of the expected output, or the program is not printing anything (printf unreachable)."])
        if args.verbose:
            print(last_vars[-1], new_map[last_vars[-1]])
    return new_map

def instrument_file(input_file, output_file, num_unroll, path_map_stu_insts, second_step_vars=None, hierarchical_weights=False, bug_assist=False):
    output_file, sincludes, includes = make_output_dir(input_file, output_file)#, logfilename, loglibpath)
    if second_step_vars:
        second_step_vars = load_dict(second_step_vars)
    try:
        ast = parse_file(output_file, use_cpp=True,
            cpp_path='g++',
            cpp_args=['-E', '-Iutils/fake_libc_include'])
    except:
        print("Error while compiling:", input_file)
        return 0

    map_stu_stmts=dict()
    # print('******************** INPUT FILE: ********************')
    v = c_ast.NodeVisitor()
    v.visit(ast)
    # ast.show()
    # exit()
    # v = VariablesVisitor()
    v2 = FunctionInlineVisitor(args.verbose)
    ast = v2.visit(ast)
    one_line_functions = v2.map_2_initial_lines
    # ast.show()
    # exit()
    v = ProgramUnrollerVisitor(inputs, outputs)
    n_ast = v.visit(ast)
    # n_ast.show()
    if args.verbose:
        print("Each loop will be unrolled {u} times.".format(u=num_unroll if num_unroll != None else v.max_offset))
    v = ProgramInstrumentalizerVisitor(num_unroll if num_unroll != None else v.max_offset, second_step_vars, bug_assist)
    gen = c_generator.CGenerator()
    n_ast = v.visit(n_ast)
    # n_ast.show()
    weights_map = v.map_stu_stmts
    visitor = RelaxVarsWeightVisitor(len(v.map_stu_stmts.keys()), num_unroll if num_unroll != None else v.max_offset, hierarchical_weights=hierarchical_weights)
    while visitor.is_another_iteration_needed():
        w_ast = deepcopy(n_ast)
        visitor.next_iteration()
        visitor.visit(w_ast)
        weights_map = visitor.get_weights_map()
    main_node = next(node for node in ast.ext if isinstance(node, c_ast.FuncDef) and node.decl.name == 'main')
    map_stu_stmts = get_complete_map_to_students_statements(main_node.coord, v.map_stu_stmts, num_unroll, ["__l_{b}__".format(b=c) for c in range(v.max_bool_cnt-2, v.max_bool_cnt+1)], one_line_functions, weights_map)
    gen_output_file(gen, n_ast, sincludes + includes, output_file)
    save_dict(map_stu_stmts, path_map_stu_insts)
    
def parser():
    parser = argparse.ArgumentParser(prog='program_instrumentalizer.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-ip', '--inc_prog', help='Program to be repaired.')
    parser.add_argument('-nu', '--num_unroll', type=int, help='Number of times each loop is going to be unrolled.')
    parser.add_argument('-o', '--output_prog', nargs='?', help='Output program (program fixed).')
    parser.add_argument('-hw', '--hierarchical_weights', action='store_true', default=False, help='The weight of each relaxation variable depends on the number of variables in its sub-AST.')    
    parser.add_argument('-msi', '--map_stu_insts', nargs='?', help='Path to store the mapping from instrumentalized-unrolled program statements to the original students\' instructions.')    
    parser.add_argument('-e', '--ipa', help='Name of the lab and exercise (IPA) so we can check the IO tests.')
    parser.add_argument('-ssv', '--second_step_vars', nargs='?', help='Second Step. Receives the IDs of some relaxation variables that should be more relaxed with nondeterministic values.')
    parser.add_argument('-fi', '--fault_index', type=int, default=0, help='Index of the set of faults to instrumentalize.')
    parser.add_argument('-t', '--test', help='Number of the IO test to use. If none, it will use all test in which the program does not return the expected output.', default="*")
    parser.add_argument('--test_dir', help='Test dir. If none, C-Pack-IPAs\' test suit is used.')
    parser.add_argument('--traces_dir', help='Traces dir. If none, the entire test suite of TCAS will be used.')            
    parser.add_argument('-upt', '--use_passed_tests', action='store_true', default=False, help='Unrolls the program also with the input and output values for passed tests.')
    parser.add_argument('-ba', '--bug_assist', action='store_true', default=False, help='Instrumentalizes for BugAssist (Does not introduce any nondeterminism).')    
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args

if __name__ == '__main__':
    args = parser()
    in_tests = glob.glob('C-Pack-IPAs/tests/{d}/*_{t}.in'.format(d=args.ipa, t=args.test) if args.test_dir is None else '{d}/tests/t{t}.in'.format(d=args.test_dir, t=args.test), recursive=True)
    inputs = get_input_values(in_tests, args.inc_prog, only_failed_tests=not args.use_passed_tests) if not args.traces_dir else get_input_values(in_tests, args.inc_prog, only_failed_tests=not args.use_passed_tests, tcas_traces=args.traces_dir)
    out_tests = glob.glob('tests_updated/{d}/*_{t}.out'.format(d=args.ipa, t=args.test) if args.test_dir is None else '{d}/tests/t{t}.out'.format(d=args.test_dir, t=args.test) , recursive=True)     
    outputs = get_output_values(out_tests, inputs)
    if args.verbose:
        print(inputs)
        print(outputs)
    instrument_file(args.inc_prog, args.output_prog, args.num_unroll, args.map_stu_insts, args.second_step_vars, args.hierarchical_weights, args.bug_assist) 
    
