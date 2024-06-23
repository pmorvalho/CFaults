#!/usr/bin/python
#Title			: helper.py
#Usage			: python helper.py -h
#Author			: pmorvalho
#Date			: May 02, 2022
#Description    	: Script with generic functions used in several scripts
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

from __future__ import print_function
import sys, os
import re
from copy import deepcopy
import argparse
from sys import argv
from shutil import copyfile
import random
from numpy import binary_repr
import pickle
import gzip
import pathlib
import glob
# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator

#-----------------------------------------------------------------

logic_bin_ops = [">", "<", ">=", "<=", "==", "!=", '||', '&&']
arith_bin_ops = ["+", "-", "*", "/", "%"]

id_dict = dict()
cur_id = 0

def reset_ids():
    global id_dict, cur_id
    id_dict = dict()
    cur_id = 0    

def node_id(coord, t=""):
    global id_dict
    global cur_id
    file = coord.file
    line = coord.line
    column = coord.column
    s = file+str(line)+str(column)+str(t)
    # print('node_id')
    # print(s)
    # print(id_dict)
    if s in id_dict.keys():
        return id_dict[s]
    else:
        id_dict[s] = cur_id
        cur_id += 1        
        return id_dict[s]

def node_repr(coord):
    file = coord.file
    line = coord.line
    column = coord.column
    return "l"+str(line)+"-c"+str(column)
    
#-----------------------------------------------------------------
def make_output_dir(input_file, output_file):
    sincludes = []
    includes = []
    noincludes = []
    with open(input_file, 'r') as reader:
        for line in reader:
            m = re.match('^\s*#\s*include\s*<', line)
            if m:
                sincludes.append(line)
            else:
                m = re.match('^\s*#\s*include', line)
                if m:
                    includes.append(line)
                else:
                    noincludes.append(line)
    # try:
    #     if not os.path.exists(output_file):
    #         os.makedirs(output_file)
    # except OSError:
    #     print("Creation of the directory {0} failed".format(output_dir))

    # output_file = output_dir + '/' + os.path.basename(input_file)
    # output_file = output_dir + '/tmp_input_file.c'
    output_file = output_file + ".c" if output_file[-2:] != ".c" else output_file
    with open(output_file, 'w') as writer:
        writer.writelines(sincludes)
        writer.writelines(includes)
        writer.write('void fakestart() {;}\n')
        writer.writelines(noincludes)

    return output_file, sincludes, includes

def get_output_file_name(filename, output_dir=None):
    if output_dir:
        return output_dir + '/' + filename + ".c"
    else:
        return filename + ".c" if filename[-2:] != ".c" else filename
    
def gen_output_file(c_gen, ast, includes, filename, output_dir=None):
    output_file = get_output_file_name(filename, output_dir)
    os.system("rm "+output_file)
    # print(ast)
    str_ast = c_gen.visit(ast)
    # print(str_ast)
    # str_ast = remove_fakestart(str_ast)
    includes.append("#include \"prints.h\"\n")    
    with open(output_file, 'w+') as writer:
        writer.writelines(includes)
        writer.write(str_ast)

def write_program(ast, c_gen, output_file, includes):
    # write a clean program without any fakestart info
    cu = CleanUpVisitor()
    ast_cleaned = cu.visit(ast)
    str_ast = c_gen.visit(ast_cleaned)
    # print(str_ast)
    includes.append("#include \"../prints.h\"\n")
    with open(output_file, 'w') as writer:
        writer.writelines(includes)    
        writer.write(str_ast)

def check_program_on_test(prog, test_id):
    lines = os.popen("./program_checker.sh {p} {t}".format(p=prog, t=test_id)).read()
    if "WRONG\n" in lines:
        return False
    return True

def get_input_values(tests, prog_path, only_failed_tests=True, tcas_traces=None):
    tests_values = dict()
    # checking if the student calls getchar() in his implementation otherwise we are going to split the input using the spaces
    traces_list = [d.split("/")[-1].replace(".out", "") for d in glob.glob(tcas_traces+"/*.out")] if tcas_traces else None
    read_chars = True if "getchar()" in "".join(open(prog_path, "r+").readlines()) else False
    for t in tests:
        if only_failed_tests and not tcas_traces and check_program_on_test(prog_path, t):
            continue
        t_id = t.split("/")[-1].split(".")[0]
        if only_failed_tests and tcas_traces and t_id not in traces_list:
            continue        
        # print(t_id)
        t_id = int(t_id.split("_")[-1]) if "_" in t_id else int(t_id[1:])
        tests_values[t_id] = dict()
        tests_values[t_id]["int"]=[]
        tests_values[t_id]["float"]=[]
        tests_values[t_id]["char"]=[]
        lines = open(t, "r+").readlines()
        t_in = []
        if lines == []:
            t_in = [""]
        for l in lines:
            if read_chars:
                t_in += l
            else:
                t_in += l.split()
        for n in range(len(t_in)):
            try:
                if not read_chars:
                    t_in[n] = int(t_in[n])
                    # tests_values[t_id]["int"].append(t_in[n])
                    # for now we are only considering float arrays because float vars can be assigned to int values
                    tests_values[t_id]["float"].append(t_in[n])
                else:
                    if "\n" == t_in[n]:
                        t_in[n] = "\'\\n\'"
                    elif '\\' == t_in[n]:
                        t_in[n] = "\'\\\\\'"
                    else:
                        t_in[n] = "\'"+str(t_in[n])+"\'"
                    tests_values[t_id]["char"].append(t_in[n])                    
            except Exception as e:
                try:
                    t_in[n] = float(t_in[n])
                    tests_values[t_id]["float"].append(t_in[n])
                except Exception as e:
                    if t_in[n]:
                        if "\n" == t_in[n]:
                            t_in[n] = "\'\\n\'"
                        elif "\\" == t_in[n]:
                            t_in[n] = "\'\\\'"
                        else:
                            t_in[n] = "\'"+str(t_in[n])+"\'"
                    else:
                        t_in[n] = ""
                    tests_values[t_id]["char"].append(t_in[n])

        if read_chars:
            tests_values[t_id]["char"].append("EOF")

    if len(tests_values.keys()) == 0:
        exit("This program is correct according to the given set of IO tests.")
    
    return tests_values

def get_output_values(tests, inputs):
    tests_values = dict()
    for t in tests:
        t_id = t.split("/")[-1].split(".")[0]
        t_id = int(t_id.split("_")[-1]) if "_" in t_id else int(t_id[1:])        
        if t_id not in inputs.keys():
            continue
        t_id = t.split("/")[-1].split(".")[0]
        t_id = int(t_id.split("_")[-1]) if "_" in t_id else int(t_id[1:])
        tests_values[t_id] = dict()
        tests_values[t_id]["char"] = open(t, "r+").readlines()
        # # REMOVE ME
        # break
    return tests_values

#-----------------------------------------------------------------
# Dicts

def load_dict(d):
    fp=gzip.open(d,'rb')
    d_map=pickle.load(fp)
    fp.close()
    return d_map

def save_dict(d, dict_name):
    # dict_name is expected to be something like "types2int.pkl.gz", and d is the dict to be saved
    fp=gzip.open(dict_name,'wb')
    pickle.dump(d,fp)
    fp.close()

#-----------------------------------------------------------------
# A visitor that removes the fakestart
class CleanUpVisitor(c_ast.NodeVisitor):
    def __init__ (self):
        super().__init__()
        
    def visit_FileAST(self, node):
        #print('****************** Found FileAST Node *******************')
        n_ext = []
        fakestart_pos = -1 #for the case of our injected function which do not have the fakestart function in their ast
        for e in range(len(node.ext)):
            x = node.ext[e]
            if fakestart_pos==-1 and isinstance(x, c_ast.FuncDef) and "fakestart" in x.decl.type.type.declname:
                fakestart_pos=e
        
        n_file_ast = c_ast.FileAST(node.ext[fakestart_pos+1:])
        return n_file_ast

    
#-----------------------------------------------------------------
# A generic visitor that visits the entire AST (at least that's the idea :') )
class ASTVisitor(c_ast.NodeVisitor):

    def __init__ (self):
        super().__init__()
        self.pn = None # parent node
        self.max_offset = 1
                        
    _method_cache = None

    def visit(self, node):
        """ Visit a node.
        """

        if self._method_cache is None:
            self._method_cache = {}

        visitor = self._method_cache.get(node.__class__.__name__, None)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        return visitor(node)

    def get_node_name(self, node):
        return node.__class__.__name__
    
    def visit_FileAST(self, node):
        #print('****************** Found FileAST Node with Parent Node ****************')
        n_ext = []
        fakestart_pos = -1 #for the case of our injected function which do not have the fakestart function in their ast
        prv_pn = self.pn
        self.pn = self.get_node_name(node)        
        for e in range(len(node.ext)):
            x = node.ext[e]
            # n_ext.append(self.visit(x, node_id(x.coord)))
            if isinstance(x, c_ast.FuncDef) and "fakestart" in x.decl.type.type.declname:
                fakestart_pos=e


        fakestart_pos = -1        
        for e in range(fakestart_pos+1, len(node.ext)):
            x = node.ext[e]
            n_ext.append(self.visit(x))

        self.pn = prv_pn
        n_file_ast = c_ast.FileAST(n_ext)
        return n_file_ast

    def visit_Decl(self, node):
        #print('****************** Found Decl Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        if not isinstance(node.type, c_ast.TypeDecl) and not isinstance(node.type, c_ast.ArrayDecl):
            if node.init is not None:
                node.init = self.visit(node.init)

            # because it can be other type of declaration. Like func declarations.
            node.type = self.visit(node.type)
            self.pn = prv_pn
            return node

        if node.init is not None:
            node.init = self.visit(node.init)

        self.pn = prv_pn    
        return node

    def visit_TypeDecl(self, node):
        #print('****************** Found Type Decl Node with Parent Node '+self.pn+'****************')
        # attrs: declname, quals, align, type
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        self.type = self.visit(node.type)
        self.pn = prv_pn 
        return node
    
    def visit_ArrayDecl(self, node):
        #print('****************** Found Array Decl Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        if node.dim is not None:
            node.dim = self.visit(node.dim)
        self.pn = prv_pn 
        return node

    def visit_PtrDecl(self, node):
        #print('****************** Found Pointer Decl Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        node.type = self.visit(node.type)
        self.pn = prv_pn
        return node

    def visit_ArrayRef(self, node):
        #print('****************** Found Array Ref Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        node.name = self.visit(node.name)
        node.subscript = self.visit(node.subscript)
        self.pn = prv_pn
        return node

    def visit_Assignment(self, node):
        #print('****************** Found Assignment Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        node.rvalue = self.visit(node.rvalue)
        node.lvalue = self.visit(node.lvalue)
        self.pn = prv_pn
        return node

    def visit_ID(self, node):
        #print('****************** Found ID Node with Parent Node '+self.pn+'****************')
        return node

    def visit_Constant(self, node):
        #print('****************** Found Constant Node with Parent Node '+self.pn+'****************')
        return node
    
    def visit_ExprList(self, node):
        #print('****************** Found ExprList Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        for e in node.exprs:
            e = self.visit(e)
        self.pn = prv_pn
        return node

    def visit_ParamList(self, node):
        #print('****************** Found ParamList Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        for e in node.params:
            e = self.visit(e)
        self.pn = prv_pn
        return node
    
    def visit_Cast(self, node):
        #print('******************** Found Cast Node with Parent Node '+self.pn+'******************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        node.expr = self.visit(node.expr)
        self.pn = prv_pn
        return node

    def visit_UnaryOp(self, node):
        #print('****************** Found Unary Operation with Parent Node '+self.pn+'*******************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        node.expr = self.visit(node.expr)
        self.pn = prv_pn
        return node

    def visit_BinaryOp(self, node):
        #print('****************** Found Binary Operation with Parent Node '+self.pn+'*******************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        left = self.visit(node.left)
        right = self.visit(node.right)
        self.pn = prv_pn
        return c_ast.BinaryOp(node.op, left, right, node.coord)

    def visit_TernaryOp(self, node):
        #print('****************** Found TernaryOp Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_cond = self.visit(node.cond)
        # if isinstance(node.iftrue, c_ast.Compound):
        n_iftrue = self.visit(node.iftrue)
        # else:
        #     n_iftrue = self.visit(c_ast.Compound([node.iftrue], node.iftrue.coord))
        
        n_iffalse = node.iffalse
        if node.iffalse is not None:
            # if not isinstance(node.iffalse, c_ast.Compound):
                # node.iffalse = c_ast.Compound([node.iffalse], node.iffalse.coord)
            node.iffalse = self.visit(node.iffalse)
        
        #print('****************** New Cond Node with Parent Node '+self.pn+'****************')
        n_ternary = c_ast.TernaryOp(n_cond, n_iftrue, n_iffalse, node.coord)
        self.pn = prv_pn
        return n_ternary

    def visit_FuncDecl(self, node):
        #print('****************** Found FuncDecl Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        if node.args:
            node.args = self.visit(node.args)
        self.pn = prv_pn
        return node

    def visit_FuncDef(self, node):
        #print('****************** Found FuncDef Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        decl = node.decl
        param_decls = node.param_decls
        if node.param_decls:
            param_decls = self.visit(node.param_decls)
        if "main" != node.decl.name and "fakestart" != node.decl.name: #ignore main function
            # if the function has parameters add them to the scope
            if decl.type.args:
                decl.type.args = self.visit(decl.type.args)
                
        body = node.body
        coord = node.coord
        n_body_1 = self.visit(body)
        n_func_def_ast = c_ast.FuncDef(decl, param_decls, n_body_1, coord)
        self.pn = prv_pn
        return n_func_def_ast

    def visit_FuncCall(self, node):
        #print('****************** Found FuncCall Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        if node.args:
            node.args = self.visit(node.args)
        self.pn = prv_pn
        return node
    
    def visit_Compound(self, node):
        #print('****************** Found Compound Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        block_items = node.block_items
        coord = node.coord
        n_block_items = []
        if block_items is not None:
            for x in block_items:
                n_block_items.append(self.visit(x))

        n_compound_ast = c_ast.Compound(n_block_items, coord)
        self.pn = prv_pn
        return n_compound_ast

    def visit_If(self, node):
        #print('****************** Found IF Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_cond = self.visit(node.cond)
        if isinstance(node.iftrue, c_ast.Compound):
            n_iftrue = self.visit(node.iftrue)
        else:
            n_iftrue = self.visit(c_ast.Compound([node.iftrue], node.iftrue.coord))

        n_iffalse = node.iffalse
        if node.iffalse is not None:
            if not isinstance(node.iffalse, c_ast.Compound):
                node.iffalse = c_ast.Compound([node.iffalse], node.iffalse.coord)
            node.iffalse = self.visit(node.iffalse)
        #print('****************** New Cond Node with Parent Node '+self.pn+'****************')
        n_if = c_ast.If(n_cond, n_iftrue, n_iffalse, node.coord)
        self.pn = prv_pn
        return n_if

    def visit_For(self, node):
        #print('****************** Found For Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_init = self.visit(node.init)
        n_cond = self.visit(node.cond)
        if isinstance(node.stmt, c_ast.Compound):
            n_stmt = self.visit(node.stmt)
        else:
            n_stmt = self.visit(c_ast.Compound([node.stmt], node.stmt.coord))
        n_next = node.next
        if n_next is not None:
            n_next = self.visit(node.next)

        n_for = c_ast.For(n_init, n_cond, n_next, n_stmt, node.coord)
        self.pn = prv_pn
        return n_for

    def visit_While(self, node):
        #print('****************** Found While Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_cond = self.visit(node.cond)
        if isinstance(node.stmt, c_ast.Compound):
            n_stmt = self.visit(node.stmt)
        else:
            n_stmt = self.visit(c_ast.Compound([node.stmt], node.stmt.coord))
        n_while = c_ast.While(n_cond, n_stmt, node.coord)
        self.pn = prv_pn
        return n_while

    def visit_DoWhile(self, node):
        #print('****************** Found DoWhile Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_cond = self.visit(node.cond)
        if isinstance(node.stmt, c_ast.Compound):
            n_stmt = self.visit(node.stmt)
        else:
            n_stmt = self.visit(c_ast.Compound([node.stmt], node.stmt.coord))
        n_dowhile = c_ast.DoWhile(n_cond, n_stmt, node.coord)
        self.pn = prv_pn
        return n_dowhile

    def visit_Switch(self, node):
        #print('****************** Found Switch Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_cond = self.visit(node.cond)
        if isinstance(node.stmt, c_ast.Compound):
            n_stmt = self.visit(node.stmt)
        else:
            n_stmt = self.visit(c_ast.Compound([node.stmt], node.stmt.coord))
        n_switch = c_ast.Switch(n_cond, n_stmt, node.coord)
        self.pn = prv_pn
        return n_switch

    def visit_Return(self, node):
        #print('****************** Found Return Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        if node.expr:
            node.expr = self.visit(node.expr)
        self.pn = prv_pn
        return node

    def visit_Break(self, node):
        #print('****************** Found Break Node with Parent Node '+self.pn+'****************')
        return node

    def visit_Continue(self, node):
        #print('****************** Found Continue Node with Parent Node '+self.pn+'****************')
        return node

    def visit_Case(self, node):
        #print('****************** Found Case Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_stmts_1 = []
        for x in node.stmts:
            n_stmts_1.append(self.visit(x))
            
        n_stmts_2 = c_ast.Compound (n_stmts_1, node.coord)
        self.pn = prv_pn
        return c_ast.Case(node.expr, n_stmts_2, node.coord)

    def visit_Default(self, node):
        #print('****************** Found Default Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_stmts_1 = []
        for x in node.stmts:
            n_stmts_1.append(self.visit(x))
            
        n_stmts_2 = c_ast.Compound(n_stmts_1, node.coord)
        self.pn = prv_pn
        return c_ast.Default(n_stmts_2, node.coord)

    def visit_EmptyStatement(self, node):
        #print('****************** Found EmptyStatement Node with Parent Node '+self.pn+'****************')
        return node

    def generic_visit(self, node):
        #print('******************  Something else ************')
        return node


class FunctionInlineVisitor(ASTVisitor):
    # Visitor that inlines all one-line functions, i.e. functions that are simply a return statement. Ignoring ternary ops.
    def __init__(self, verbose):
        self.inline_functions = {}
        self.map_2_initial_lines = {}
        self.verbose = verbose
        super().__init__()

    def visit_FileAST(self, node):
        #print('****************** Found FileAST Node with Parent Node ****************')
        n_ext = []
        fakestart_pos = -1 #for the case of our injected function which do not have the fakestart function in their ast
        for e in range(len(node.ext)):
            x = node.ext[e]
            # n_ext.append(self.visit(x, node_id(x.coord)))
            n_ext.append(x)
            if isinstance(x, c_ast.FuncDef) and "fakestart" in x.decl.type.type.declname:
                fakestart_pos=e
                break
            
        for e in range(fakestart_pos+1, len(node.ext)):
            x = node.ext[e]
            xv = self.visit(x)
            if not (isinstance(xv, c_ast.FuncDef) and xv.decl.name in self.inline_functions.keys()):                
                n_ext.append(xv)

        n_file_ast = c_ast.FileAST(n_ext)
        return n_file_ast
        
    def visit_FuncDef(self, node):
        # Check if the function has only one statement and it is a return statement
        if (
            isinstance(node.body, c_ast.Compound)
            and len(node.body.block_items) == 1
            and isinstance(node.body.block_items[0], c_ast.Return)            
        ):
            if isinstance(node.body.block_items[0].expr, c_ast.TernaryOp):
                return node
            func_name = node.decl.name
            return_expr = node.body.block_items[0].expr
            self.inline_functions[func_name] = (node.decl, return_expr)
            return node    
        else:
            node.body = self.visit(node.body)
            return node

    def visit_FuncCall(self, node):
        # Replace function calls with the inlined return expression
        if isinstance(node.name, c_ast.ID) and node.name.name in self.inline_functions:
            decl, return_expr = self.inline_functions[node.name.name]
            # Perform variable substitution
            if node.args:
                for i, arg in enumerate(node.args.exprs):
                    if isinstance(arg, c_ast.ID):
                        # Substitute variable names
                        arg.name = decl.decl.type.args.params[i].name
            return_expr = deepcopy(return_expr)
            c = int(str(node.coord).split(":")[1])
            oneline_func_name = decl.type.type.declname
            orig_ln = int(str(return_expr.coord).split(":")[1])
            if c not in self.map_2_initial_lines.keys():
                self.map_2_initial_lines[c] = [(orig_ln, oneline_func_name)]
            else:
                self.map_2_initial_lines[c].append((orig_ln, oneline_func_name))
            if self.verbose:
                print("Lineno {ln} inlining {fn} (lineno {ln2})".format(ln=c, fn=oneline_func_name, ln2=orig_ln))
            return_expr.coord = node.coord
            
            return return_expr
        else:
            node = self.generic_visit(node)
            return node
        
if __name__ == '__main__':
    pass
