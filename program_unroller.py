#!/usr/bin/python
#Title			: program_unroller.py
#Usage			: python program_unroller.py -h
#Author			: pmorvalho
#Date			: May 08, 2023
#Description		: Unrolls a program using a different iteration for each IO test. Injects assertions into the end of each test scope. 
#Notes			: Swaps scanfs with read operations to input arrays. A different input/output array for each test.
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
import re
import glob


from program_instrumentalizer import *

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator

from helper import *

# def remove_after_return(node):
#     block_items = node.block_items
#     coord = node_id(node.coord)
#     n_block_items = []
#     if block_items is not None:
#         for x in block_items:
#             if not isinstance(x, c_ast.Return):
#                 n_block_items.append(x)
#             else:
#                 node.block_items=n_block_items
#                 return x
#     return None

def get_input_arrays(test_id, coord, inputs, scope_vars):
    decls = []
    max_offset = 0
    for t in ["int", "float", "char"]:
        in_name = "__input_{t}".format(t=t,i=test_id)
        in_offset_name = "__input_offset_{t}".format(t=t,i=test_id)            
        values=[]
        for v in inputs[test_id][t]:
            values.append(c_ast.Constant(t, str(v), coord=coord))

        if values != []:
            l = str(len(inputs[test_id][t]))
            decls.append(c_ast.Decl(in_name, [], [], [], [],                            
                                   c_ast.ArrayDecl(c_ast.TypeDecl(in_name,
                                                                  [],
                                                                  None,
                                                                  c_ast.IdentifierType([t], coord=coord),
                                                                  coord=coord),
                                            c_ast.Constant(t,l, coord=coord),
                                            [],
                                            coord=coord),
                                   c_ast.InitList(values),
                                   None,
                                   coord=coord))
            if int(l) > max_offset:
                max_offset = int(l)
            decls.append(c_ast.Decl(in_offset_name, [], [], [], [],                            
                                   c_ast.TypeDecl(in_offset_name,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType(["int"], coord=coord),
                                                  coord=coord),
                                   c_ast.Constant(t,str(0)),
                                   None,
                                   coord=coord))
            scope_vars[in_offset_name] = "int"
            scope_vars[in_name] = t
    return decls, max_offset

def get_output_decl(test_id, coord, outputs, scope_vars):
    global out_name, out_offset_name
    decls = []
    t="char"    
    # for t in ["int", "float", "char"]:
    output_str = "\""+"".join(outputs[test_id]["char"]).replace('\\',"\\\\").replace("\n", "\\n").replace('"',"\\\"")+"\""    
    out_name = "__output_{t}".format(t=t,i=test_id)
    out_offset_name = "__output_offset_{t}".format(t=t,i=test_id)
    # output_len = sum(len(s.replace("\n", "\\n")) for s in outputs[test_id]["char"])
    output_len = sum(len(s) for s in outputs[test_id]["char"])+1
    decls.append(c_ast.Decl(out_name, [], [], [], [],                            
                            c_ast.ArrayDecl(c_ast.TypeDecl(out_name,
                                                           [],
                                                           None,
                                                           c_ast.IdentifierType([t], coord=coord),
                                                           coord=coord),
                                            c_ast.Constant(t,str(output_len), coord=coord),
                                            [],
                                            coord=coord),
                                   c_ast.Constant("char", output_str, coord=coord),
                                   None,
                                   coord=coord))
    scope_vars[out_name] = t
    t="int"
    decls.append(c_ast.Decl(out_offset_name, [], [], [], [],                            
                                   c_ast.TypeDecl(out_offset_name,
                                                  [],
                                                  None,
                                                  c_ast.IdentifierType(["int"], coord=coord),
                                                  coord=coord),
                                   c_ast.Constant(t,str(0)),
                                   None,
                                   coord=coord))
    scope_vars[out_offset_name] = t
        # elif outputs[test_id][t] != []:
        #     decls.append(c_ast.Decl(out_name, [], [], [], [],                            
        #                            c_ast.TypeDecl(out_name,
        #                                           [],
        #                                           None,
        #                                           c_ast.IdentifierType([t], coord=coord),
        #                                           coord=coord),
        #                            None,
        #                            None,
        #                            coord=coord))
    return decls, output_len


def get_test_output_assertions(test_id, coord, outputs):
    decls = []
    t="char"
    out_name = "__output_{t}".format(t=t,i=test_id)
    output_str = "\""+"".join(outputs[test_id]["char"]).replace('\\',"\\\\").replace("\n", "\\n").replace('"',"\\\"")+"\""
    decls.append(c_ast.FuncCall(c_ast.ID("assert", coord=coord),
                                c_ast.ExprList([c_ast.BinaryOp("!=",
                                                               c_ast.FuncCall(c_ast.ID("strcmp", coord=coord),
                                                                              c_ast.ExprList([c_ast.ID(out_name, coord=coord), c_ast.Constant("char", output_str, coord=coord)], coord=coord)), c_ast.Constant("int", 0, coord=coord), coord=coord)],
                                               coord=coord)))
    # decls[-1].show()
    return decls

def get_output_assertions(outputs, coord):
    decls = []
    complete_cond=None
    t="char"
    for test_id in outputs.keys():
        out_name = "__output_{t}__{i}".format(t=t,i=test_id)
        output_str = "\""+"".join(outputs[test_id]["char"]).replace('\\',"\\\\").replace("\n", "\\n").replace('"',"\\\"")+"\""
        new_cond = c_ast.BinaryOp("!=",c_ast.FuncCall(c_ast.ID("strcmp", coord=coord),
                                       c_ast.ExprList([c_ast.ID(out_name, coord=coord), c_ast.Constant("char", output_str, coord=coord)], coord=coord)), c_ast.Constant("int", 0, coord=coord), coord=coord)
        if complete_cond == None:
            complete_cond=new_cond
        else:
            complete_cond = c_ast.BinaryOp("||", complete_cond, new_cond, coord=coord)

    assert(complete_cond != None)
    return c_ast.FuncCall(c_ast.ID("assert", coord=coord),
                                c_ast.ExprList([complete_cond],
                                               coord=coord))



# Old version of this function, we would look into the type of each paramenter
# def get_print_function_name(node, scope_vars):
#     if isinstance(node, c_ast.ID) or isinstance(node, c_ast.FuncCall):
#         var_name = node.name if isinstance(node, c_ast.ID) else node.name.name
#         if scope_vars[var_name] == "char":
#             fname = "printChars"
#         elif scope_vars[var_name] == "float":
#             fname = "printFloat"
#         elif scope_vars[var_name] == "int":                    
#             fname = "printInt"
#         return fname
#     elif isinstance(node, c_ast.TernaryOp):
#         return get_print_function_name(node.iftrue, scope_vars)
#     elif isinstance(node, c_ast.Constant):
#         if node.type == "string":
#             fname = "printChars"
#         elif node.type == "float":
#             fname = "printFloat"
#         elif node.type == "int":                    
#             fname = "printInt"
#         return fname


def get_print_function_name(pattern):
    if "s" in pattern:
        fname = "printChars"
    elif "d" in pattern or "i" in pattern or "u" in pattern:
        fname = "printInt"
    elif "f" in pattern:
        fname = "printFloat"
    elif "c" in pattern:
        fname = "printChar"
    else:
        print("Warning: It appears that you may be attempting to use an incorrect base for integer numbers in the printf format string. For hexadecimal numbers (base-16), use %x, and for decimal numbers (base-10), use %d. Verify that the format specifier matches the intended numeric base to avoid unexpected output or errors. Currently, we only support integers (%d/%i), floats (%f), strings (%s), chars (%c).")        
        exit(1)
        
    return fname


#-----------------------------------------------------------------
class ProgramUnrollerVisitor(ASTVisitor):

    def __init__ (self, inputs, outputs, assertions=True, verbose=False):
        super().__init__()
        # after_fakestart
        self.after_fakestart = False
        # dic with the information about the Input tests
        self.inputs = inputs
        # info about the output tests
        self.outputs = outputs
        # decls
        self.input_decls = []
        self.output_decls = []
        self.functions_renamed = []
        self.test_id = None
        self.first_block = False
        self.first_check = False
        self.assign_node = None
        self.var_initialization= None
        # to inject or not to inject assertions when unrolling the program
        self.inject_assertions = True if assertions else False
        # to keep track of the enums values
        self.enums = dict()
        # list with the program variables
        self.scope_vars = dict()
        # flag to use while checking an if-statement
        self.check_simple_if_else = False
        # dict with infromations about the variables declared inside each scope
        self.blocks_vars = dict()
        # uninitialized global variables
        self.uninitialized_global_vars = list()
        # flag to know if we are inside a variable declaration
        self.declaring_var = False
        # variable to know the coord of the current block
        self.curr_block = "global"
        # variable to know the name of the current variable being declared
        self.curr_var = None        
        # info aboout the variable declaration for each code block
        self.blocks_vars[self.curr_block] = dict()
        self.blocks_vars[self.curr_block]["decls_id"] = []
        self.blocks_vars[self.curr_block]["dims"] = dict()        
        # translating for-loops into while-loops
        self.found_continue = False
        # label for gotos
        self.next_label = None
        # current function name
        self.curr_func_name = None
        # instruction to inject before the gotos 
        self.stmts_before_goto = None
        # verbose
        self.verbose = verbose

    def initialize_global_vars(self, coord):
        inits = []
        for v in self.uninitialized_global_vars:
            if v in self.blocks_vars["global"]["dims"].keys():
                t = self.scope_vars[v].split("_")[1]                
                for d in range(self.blocks_vars["global"]["dims"][v]):
                    init = c_ast.FuncCall(name=c_ast.ID(name='nondet_'+t, coord=coord), args=None, coord=coord)
                    inits.append(c_ast.Assignment('=', c_ast.ArrayRef(c_ast.ID(v, coord), c_ast.Constant("int", str(d), coord=coord), coord), init, coord))
            else:
                t = self.scope_vars[v]
                init = c_ast.FuncCall(name=c_ast.ID(name='nondet_'+t, coord=coord), args=None, coord=coord)
                inits.append(c_ast.Assignment('=', c_ast.ID(v, coord), init, coord))
        return inits
        
    def visit(self, node):
        #node.show()
        return c_ast.NodeVisitor.visit(self, node)

    def visit_FileAST(self, node):
        #print('****************** Found FileAST Node *******************')
        n_ext = []
        fakestart_pos = -1 #for the case of our injected function which do not have the fakestart function in their ast
        for e in range(len(node.ext)):
            x = node.ext[e]
            n_ext.append(self.visit(x))
            if fakestart_pos==-1 and isinstance(x, c_ast.FuncDef) and "fakestart" in x.decl.type.type.declname:
                fakestart_pos=e
                self.after_fakestart = True
                tests=list(self.inputs.keys())
                tests.sort()
                # for t_id in tests[:-1]:
                for t_id in tests:                
                    self.test_id = t_id
                    input_decls, i_len = get_input_arrays(self.test_id, x.coord, self.inputs, self.scope_vars)
                    self.max_offset = max(i_len, self.max_offset)
                    for i in input_decls:
                        n_ext.append(self.visit(i))
                    output_decls, o_len = get_output_decl(self.test_id, x.coord, self.outputs, self.scope_vars)
                    self.max_offset = max(o_len, self.max_offset)
                    for o in output_decls:
                        n_ext.append(self.visit(o))
                self.test_id = None
                continue
            
            if self.after_fakestart and not (isinstance(x, c_ast.FuncDef) and "main" == x.decl.type.type.declname):
                tests=list(self.inputs.keys())
                tests.sort()
                x = node.ext[e]
                if isinstance(x, c_ast.Decl) and isinstance(x.type, c_ast.FuncDecl):
                    # pass # not unrolling auxiliary fuctions
                    # declarations for each different incorrect tests
                    # NOTE: We need to unroll all the auxiliary
                    # functions for each incorrect test because these
                    # functions might call print functions that need
                    # specific output vars and offsets depending on
                    # the test.
                    x = n_ext[-1]
                    n_ext.pop(-1)
                    for tid in tests:
                        n = deepcopy(x)
                        declname = n.type.type.declname
                        self.functions_renamed.append(declname)
                        n.type.type.declname = declname + "__"+str(tid)
                        n_ext.append(n)
                elif isinstance(x, c_ast.Decl) and isinstance(x.type, c_ast.TypeDecl) and isinstance(x.type.type, c_ast.IdentifierType):
                        x = n_ext[-1]
                        n_ext.pop(-1)
                        for tid in tests:
                            n = deepcopy(x)
                            declname = n.type.declname
                            n.type.declname = declname + "__"+str(tid)
                            n_ext.append(n)
                elif isinstance(x, c_ast.Decl) and isinstance(x.type, c_ast.ArrayDecl) and isinstance(x.type.type, c_ast.TypeDecl):
                        x = n_ext[-1]
                        n_ext.pop(-1)
                        for tid in tests:
                            n = deepcopy(x)
                            declname = n.type.type.declname
                            n.type.type.declname = declname + "__"+str(tid)
                            n_ext.append(n)
                elif isinstance(x, c_ast.FuncDef):
                    # pass # not unrolling auxiliary fuctions for each different incorrect tests
                    # NOTE: We need to unroll all the auxiliary
                    # functions for each incorrect test because these
                    # functions might call print functions that need
                    # specific output vars and offsets depending on
                    # the test.                    
                    x = n_ext[-1]
                    n_ext.pop(-1)
                    for tid in tests:
                        n = deepcopy(x)
                        declname = n.decl.type.type.declname
                        self.functions_renamed.append(declname)
                        n.decl.type.type.declname = declname + "__"+str(tid)
                        n_ext.append(self.visit(n))
                elif isinstance(x, c_ast.Typedef) and x.name == "bool":
                    n_ext.pop(-1)

        n_file_ast = c_ast.FileAST(n_ext[fakestart_pos+1:])
        if self.blocks_vars[self.curr_block]["decls_id"] == []:
            del self.blocks_vars[self.curr_block]
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
                if node.init != None and self.first_check:
                    init = node.init
                    node.init = None
                    self.var_initialization = c_ast.Assignment('=', c_ast.ID(node.type.type.declname, node.coord), init, node.coord)
                declname=node.type.type.declname                
                self.scope_vars[declname] = node.type.type.type.names[0]
                if self.test_id is not None and declname in self.scope_vars.keys():
                    node.type.type.declname = declname + "__"+str(self.test_id)
                return node        
            elif isinstance(node.type, c_ast.ArrayDecl):
                if node.init != None and self.first_check:
                    init = node.init
                    node.init = None
                    self.var_initialization = c_ast.Assignment('=', c_ast.ID(node.type.type.declname, node.coord), init, node.coord)
                elif node.init == None and isinstance(node.type.type, c_ast.TypeDecl) and self.curr_func_name == None:
                    self.uninitialized_global_vars.append(node.type.type.declname)
                # elif node.init == None and isinstance(node.type.type, c_ast.TypeDecl) and node.type.type.declname == "Positive_RA_Alt_Thresh":
                #     node.init = c_ast.InitList([c_ast.Constant("int", str(i), coord=node.coord) for i in [400, 500, 640, 740]])       
                # elif node.init == None and self.first_check:
                    # self.var_initialization = c_ast.Assignment('=', c_ast.ID(node.type.type.declname, node.coord), c_ast.Constant("int",str(0), node.coord), node.coord)                    
                return node
        # node.show()
        declname = node.name
        if isinstance(node.type.type, c_ast.Enum):
            type = node.type.type
        else:
            type = node.type
            while not isinstance(type, c_ast.IdentifierType):
                type = type.type
                if isinstance(type, c_ast.TypeDecl):
                    declname = type.declname
            type = type.names[0]
            
        if self.curr_block is not None:
            self.blocks_vars[self.curr_block]["decls_id"].append(node_id(node.coord))
        self.scope_vars[node.name] = type
        if self.test_id is not None and declname in self.scope_vars.keys():
            node.name = node.name + "__"+str(self.test_id)
            if isinstance(node.type, c_ast.TypeDecl):
                node.type.declname = node.type.declname + "__"+str(self.test_id)
            else:
                node.type.type.declname = node.type.type.declname + "__"+str(self.test_id)
        self.curr_var = node.name
        
        if node.init != None:
            node.init = self.visit(node.init)            
        elif self.curr_block == "global" and node.name not in ["argc", "argv"] and self.curr_func_name == None:
            self.uninitialized_global_vars.append(node.name)            

        self.curr_var = None

        if node.init != None and self.first_check:
            init = node.init
            node.init = None
            self.var_initialization = c_ast.Assignment('=', c_ast.ID(node.type.declname, node.coord), init, node.coord)
        # elif node.init == None and self.first_check:
        #     self.var_initialization = c_ast.Assignment('=', c_ast.ID(node.type.declname, node.coord), c_ast.Constant("int",str(0), node.coord), node.coord)                    

        return node


    def visit_ArrayDecl(self, node):
        #print('****************** Found ArrayDecl Node *******************')
        if isinstance(node.type, c_ast.TypeDecl):
            if self.curr_block is not None:
                self.blocks_vars[self.curr_block]["decls_id"].append(node_id(node.coord))
                self.blocks_vars[self.curr_block]["dims"][node.type.declname] = int(node.dim.value)
                
            self.scope_vars[node.type.declname] = "array_"+node.type.type.names[0]
            self.curr_var = node.type.declname

            if self.test_id is not None and node.type.declname in self.scope_vars.keys():
                node.type.declname = node.type.declname + "__"+str(self.test_id)

        return node

    def visit_ArrayRef(self, node):
        # print('****************** Found ArrayRef Node *******************')
        node.name = self.visit(node.name)
        node.subscript = self.visit(node.subscript)
        # node.show()        
        return node
    
    def visit_Assignment(self, node):
        # print('****************** Found Assignment Node *******************')
        # node.show()
        node.rvalue = self.visit(node.rvalue)    
        node.lvalue = self.visit(node.lvalue)
        if isinstance(node.rvalue, c_ast.Compound):  # when we return the scanf inside a block, and the students want the returning value of the scanf (or other function)
            # node.show()
            node.rvalue = node.rvalue.block_items[0]
        return node

    def visit_ID(self, node):
        # print('****************** Found ID Node *******************')
        if self.test_id is not None and node.name in self.scope_vars.keys() and node.name not in ["argc", "argv"]:
            node.name += "__"+str(self.test_id)

        if node.name == "argc":
            arg_name = "__input_{t}".format(t="float")
            return self.visit(c_ast.FuncCall(c_ast.ID("sizeof", node.coord), c_ast.ExprList([c_ast.ID(arg_name, node.coord)], node.coord), node.coord))
        return node
 
    def visit_Enum(self, node):
        # #print('****************** Found Enum Node *******************')
        # insert each enum on the .h file, after the scope functions of the fakestart function
        return node
    
    def visit_ExprList(self, node):
        #print('****************** Found ExprList Node *******************')
        for e in node.exprs:
            e = self.visit(e)
        return node

    def visit_UnaryOp(self, node):
        #print('****************** Found Unary Operation *******************')
        node.expr = self.visit(node.expr)
        return node
    
    def visit_BinaryOp(self, node):
        # print('****************** Found Binary Operation *******************')
        # print(node.show())
        left = self.visit(node.left)
        right = self.visit(node.right)
        return c_ast.BinaryOp(node.op, left, right, node.coord)

    def visit_TernaryOp(self, node):
        # print('****************** Found Ternary Op Node *******************')
        if_id = node_id(node.coord)
        n_cond = self.visit(node.cond)
        n_iftrue = self.visit(node.iftrue)
        n_iffalse = node.iffalse
        # if there exists and else statement
        if n_iffalse is not None:
            n_iffalse = self.visit(n_iffalse)
        #print('****************** New Cond Node *******************')
        n_ternary =  c_ast.TernaryOp(n_cond, n_iftrue, n_iffalse, node.coord)
        return n_ternary

    def visit_FuncDef(self, node):
        #print('****************** Found FuncDef Node *******************')
        param_decls = node.param_decls
        fname = node.decl.type.type.declname
        self.curr_func_name = fname
        if self.after_fakestart and "__" in fname:
            self.test_id = int(fname.split("__")[1])
        if node.decl.type.args:
            node.decl.type.args = self.visit(node.decl.type.args)
            
        body = node.body
        coord = node.coord
        self.first_check = True
        n_body_1 = self.visit(body)
        self.first_check = False            
        if "main" != fname:
            n_func_def_ast = c_ast.FuncDef(node.decl, param_decls, n_body_1, coord)
        else:
            global_vars_inits = []
            if self.initialize_global_vars:
                global_vars_inits = self.initialize_global_vars(node.coord)
                n_body_1.block_items = global_vars_inits + n_body_1.block_items
                if self.verbose:
                    print("Uninitialized global vars:", self.uninitialized_global_vars)
                    print(self.blocks_vars[self.curr_block]["dims"])
            block=[]
            tests=list(self.inputs.keys())
            tests.sort()
            # for t_id in tests[:-1]:
            for ti in range(len(tests)):
                t_id = tests[ti]
                self.test_id = t_id                
                self.next_label = "scope_{t}".format(t=tests[ti+1]) if (ti+1) < len(tests) else "final_step"
                block.append(c_ast.Label("scope_{t}".format(t=t_id), deepcopy(n_body_1), node.coord))
                # self.first_block = True
                # ret_node = remove_after_return(block[-1])

                ## adding \0 to the end of the output string
                out_name = "__output_{t}".format(t="char")
                out_offset_name = "__output_offset_{t}".format(t="char")
                # c_ast.UnaryOp("p++", c_ast.ID(out_offset_name, node.coord), node.coord)
                lvalue = c_ast.ArrayRef(c_ast.ID(out_name, node.coord), c_ast.ID(out_offset_name, node.coord), node.coord)
                # comment the following lines to remove the insertion of \n at the end of the output (always)
                # if output[offset-1 ] != "\n" then output[offset++] = "\n"
                p_lvalue = c_ast.ArrayRef(c_ast.ID(out_name, coord=node.coord), c_ast.BinaryOp("-", c_ast.ID(out_offset_name, node.coord), c_ast.Constant("int", 1, coord=coord), coord=node.coord), coord=node.coord)
                self.stmts_before_goto = c_ast.Compound([c_ast.If(c_ast.BinaryOp("!=", p_lvalue, c_ast.Constant("string", "\'"+str("\\n")+"\'", node.coord), node.coord), c_ast.Assignment('=', c_ast.ArrayRef(c_ast.ID(out_name, node.coord), c_ast.UnaryOp("p++", c_ast.ID(out_offset_name, node.coord), node.coord)), c_ast.Constant("string", "\'"+str("\\n")+"\'", node.coord), node.coord), None, node.coord), c_ast.Assignment('=', lvalue, c_ast.Constant("string", "\'"+str("\\0")+"\'", node.coord), node.coord)], node.coord)
                ## Now we are adding this instruction when we replace the return nodes by Goto nodes
                # insert_index=-2
                # if not isinstance(block[-1].stmt.block_items[-1], c_ast.Goto):
                #     insert_index=-1
                # block[-1].stmt.block_items.insert(insert_index, c_ast.If(c_ast.BinaryOp("!=", p_lvalue, c_ast.Constant("string", "\'"+str("\\n")+"\'", node.coord), node.coord), c_ast.Assignment('=', c_ast.ArrayRef(c_ast.ID(out_name, node.coord), c_ast.UnaryOp("p++", c_ast.ID(out_offset_name, node.coord), node.coord)), c_ast.Constant("string", "\'"+str("\\n")+"\'", node.coord), node.coord), None, node.coord))
                # block[-1].stmt.block_items.insert(insert_index, c_ast.Assignment('=', lvalue, c_ast.Constant("string", "\'"+str("\\0")+"\'", node.coord), node.coord))

                
                # block[-1] = self.visit(block[-1])                
                # if self.inject_assertions:
                #     # now we are only using a single assertion 
                #     # block[-1].block_items += get_test_output_assertions(self.test_id, coord, self.outputs)
                # else:
                if not self.inject_assertions:                    
                    block[-1].stmt.block_items += [c_ast.FuncCall(c_ast.ID("print", coord=coord), c_ast.ExprList([c_ast.Constant("string", "\"%s\"", coord=coord), c_ast.ID("__output_{t}".format(t="char",i=self.test_id), coord=coord)], coord=coord),  coord=coord)]
                # if max(tests) == t_id:
                    # if self.inject_assertions:                    
                    #     # block[-1].block_items += get_test_output_assertions(self.test_id, coord, self.outputs)
                    #     block[-1].block_items += get_output_assertions(self.outputs, coord)
                    # # if ret_node != None:
                    # #     block[-1].block_items += [ret_node]
                # block[-1] = self.visit(block[-1])
                block[-1] = self.visit(block[-1])

            if self.inject_assertions:
                block.append(c_ast.Label("final_step", get_output_assertions(self.outputs, coord), node.coord))
                block[-1] = self.visit(block[-1])                
            # block[-1].stmt = self.visit(block[-1].stmt)
            # self.test_id = tests[-1]
            # self.first_block = True
            # if self.inject_assertions:
            #     n_body_1.block_items.insert(-1, get_test_output_assertions(self.test_id, coord, self.outputs)[0])
            # else:
            #     n_body_1.block_items.insert(-1,c_ast.FuncCall(c_ast.ID("print", node.coord), c_ast.ExprList([c_ast.Constant("string", "\"%s\"", node.coord), c_ast.ID("__output_{t}".format(t="char",i=self.test_id), node.coord)], node.coord)))
            #     n_body_1 = self.visit(n_body_1)            
            # main_block = c_ast.Compoundlock+[n_body_1], coord)
            # n_func_def_ast = c_ast.FuncDef(decl, param_decls,main_block, coord)
            
            n_func_def_ast = c_ast.FuncDef(node.decl, param_decls, c_ast.Compound(block, coord), coord)
        self.test_id = None
        self.stmts_before_goto = None
        return n_func_def_ast

    def visit_FuncCall(self, node):
        #print('****************** Found FuncCall Node *******************')
        fname = node.name.name
        if node.args:
            # if node.name.name == "printChars" or node.name.name == "printInt" or node.name.name == "printFloat" or node.name.name == "printChar":
            #     node.args.exprs.insert(0, c_ast.ID("__output_{t}".format(t="char")))
            #     node.args.exprs.insert(1, c_ast.ID("__output_offset_{t}".format(t="char")))
            node.args = self.visit(node.args)        

        if fname == "fprintf":
            fname = "printf"
            node.args.exprs = node.args.exprs[1:]
        if fname == "printf":
            exprs = node.args.exprs            
            sformat = exprs[0].value if isinstance(exprs[0], c_ast.Constant) and exprs[0].type == "string" else " %s\n"
            params = exprs[1:] if isinstance(exprs[0], c_ast.Constant) and exprs[0].type == "string" else exprs
            # pattern = r"(%[0-9]*[a-zA-Z])" # '\%\.{0,1}[0-9]*[dfis]'
            pattern = r"(%(?:[-+0# ]*\d*(?:\.\d*)?[hlL]?[diouxXeEfFgGcrs]))"  #  I asked ChatGPT for this pattern. "In this updated implementation, the regular expression (%(?:[-+0# ]*\d*(?:\.\d+)?[hlL]?[diouxXeEfFgGcrs])) is used to capture all valid printf-style format specifiers. This includes precision (.), width (\d), and other formatting options like flags (-, +, 0, #, and space), length modifiers (h, l, L), and conversion characters (d, i, o, u, x, X, e, E, f, F, g, G, c, r, s)."
            results = re.split(pattern, str(sformat[1:-1]))
            # The resulting results list contains the parts of the format string, where the odd-indexed elements (indices 1, 3, 5, ...) correspond to the captured parameter placeholders. The even-indexed elements (indices 0, 2, 4, ...) correspond to the other parts of the format string.
            block = []
            splits = results[::2]  # to get the elements after the split pattern
            patterns_found = results[1::2]  # to get the patterns found
            # print(splits)
            # print(patterns_found)
            for i in range(len(splits)):
                if splits[i] != '':
                    fname = "printChars"
                    block.append(c_ast.Assignment('=', c_ast.ID("__output_offset_{t}".format(t="char"), coord=node.coord), c_ast.FuncCall(c_ast.ID(fname, node.coord), c_ast.ExprList([c_ast.ID("__output_{t}".format(t="char"), node.coord), c_ast.ID("__output_offset_{t}".format(t="char"), node.coord), c_ast.Constant("string", "\""+str(splits[i])+"\"", coord=node.coord)], coord=node.coord), coord=node.coord), coord=node.coord))
                if i < len(params):                    
                    fname = get_print_function_name(patterns_found[i])
                    block.append(c_ast.Assignment('=', c_ast.ID("__output_offset_{t}".format(t="char"), coord=node.coord), c_ast.FuncCall(c_ast.ID(fname, node.coord), c_ast.ExprList([c_ast.ID("__output_{t}".format(t="char"), node.coord), c_ast.ID("__output_offset_{t}".format(t="char"), node.coord), params[i]], coord=node.coord), coord=node.coord), coord=node.coord))            
            return c_ast.Compound(block, coord=node.coord)

        # if fname == "print":
        #     node.name.name = "printf"

        if fname == "scanf":
            lst = []
            for a in node.args.exprs[1:]:
                if isinstance(a, c_ast.UnaryOp):
                    lvalue = a.expr                   
                    var_name = a.expr.name.split("__")[0] if not isinstance(a.expr.name, c_ast.ID) else a.expr.name.name.split("__")[0]
                    if var_name in self.scope_vars.keys():
                        t="int"
                        in_name = "__input_{t}".format(t="float") if t == "int" or t == "float" else "__input_{t}".format(t=t)
                        in_offset_name = "__input_offset_{t}".format(t="float") if t == "int" or t == "float" else "__input_offset_{t}".format(t=t)
                        rvalue = c_ast.ArrayRef(c_ast.ID(in_name, a.coord), c_ast.UnaryOp("p++", c_ast.ID(in_offset_name, a.coord), a.coord), coord=a.coord)
                        for t in ["int", "float", "char"]:
                            if t in self.scope_vars[var_name]:                                
                                in_name = "__input_{t}".format(t="float") if t == "int" or t == "float" else "__input_{t}".format(t=t)
                                in_offset_name = "__input_offset_{t}".format(t="float") if t == "int" or t == "float" else "__input_offset_{t}".format(t=t)
                                rvalue = c_ast.ArrayRef(c_ast.ID(in_name, a.coord), c_ast.UnaryOp("p++", c_ast.ID(in_offset_name, a.coord), a.coord), coord=a.coord)
                    else:
                        raise("Variable ",var_name," not found!!")
                    rvalue = self.visit(rvalue)
                    lst.append(c_ast.Assignment("=", lvalue, rvalue, coord=a.coord))
            return c_ast.Compound(lst, coord=node.coord)

        if fname == "atoi":
            ## FIXME
            # and node.args.exprs[0].name == 'argv':
            in_name = "__input_{t}".format(t="float")
            in_offset_name = "__input_offset_{t}".format(t="float")
            rvalue = c_ast.ArrayRef(c_ast.ID(in_name, node.coord), c_ast.UnaryOp("p++", c_ast.ID(in_offset_name, node.coord), node.coord), coord=node.coord)
            rvalue = self.visit(rvalue)
            return rvalue
        
        if fname == "getchar":
            in_name = "__input_{t}".format(t="char")
            in_offset_name = "__input_offset_{t}".format(t="char")
            rvalue = c_ast.ArrayRef(c_ast.ID(in_name, coord=node.coord), c_ast.UnaryOp("p++", c_ast.ID(in_offset_name, node.coord), coord=node.coord), coord=node.coord)
            # rvalue = self.visit(rvalue)
            return rvalue

        
        if fname == "putchar":
            fname = "printChar"
            node.args.exprs.insert(0, c_ast.ID("__output_{t}".format(t="char"), coord=node.coord))
            node.args.exprs.insert(1, c_ast.ID("__output_offset_{t}".format(t="char"), coord=node.coord))            
            return c_ast.Assignment('=', c_ast.ID("__output_offset_{t}".format(t="char"), coord=node.coord), c_ast.FuncCall(c_ast.ID(fname), node.args, coord=node.coord), coord=node.coord)

        if fname == "puts":
            fname = "printChars"            
            node.args.exprs[0].value = "".join([node.args.exprs[0].value[:-1], "\\n\""])
            node.args.exprs.insert(0, c_ast.ID("__output_{t}".format(t="char"), coord=node.coord))
            node.args.exprs.insert(1, c_ast.ID("__output_offset_{t}".format(t="char"), coord=node.coord))                        
            return c_ast.Assignment('=', c_ast.ID("__output_offset_{t}".format(t="char"), coord=node.coord), c_ast.FuncCall(c_ast.ID(fname), node.args, coord=node.coord), coord=node.coord)

        if fname == "assert":
             return node
        
        if fname in self.functions_renamed and self.test_id != None:
            node.name.name = fname  + "__"+str(self.test_id)
        return c_ast.FuncCall(node.name, node.args, coord=node.coord)

    def visit_ExprList(self, node):
        # print('****************** Found ExprList Node *******************')
        for e in range(len(node.exprs)):
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
        coord = node_id(node.coord)
        self.curr_block = str(coord)
        self.blocks_vars[self.curr_block] = dict()
        self.blocks_vars[self.curr_block]["decls_id"] = []
        self.blocks_vars[self.curr_block]["dims"] = dict()        
                
        n_block_items = []            
        if block_items is not None:
            for x in block_items:
                if isinstance(x, c_ast.Decl):
                    self.declaring_var = True
                    n_block_items.append(self.visit(x))
                    if self.var_initialization != None:
                        n_block_items.append(self.visit(self.var_initialization))
                        self.var_initialization = None
                else:
                    n_block_items.append(self.visit(x))
                
                self.declaring_var = False
                self.curr_block = str(coord)
                
        self.curr_block = "global"
        n_compound_ast = c_ast.Compound(n_block_items, node.coord)
        return n_compound_ast

    def visit_If(self, node):
        #print('****************** Found IF Node *******************')
        if_id = node_id(node.coord)
        n_cond = self.visit(node.cond)
        if isinstance(node.iftrue, c_ast.Compound):
            n_iftrue = self.visit(node.iftrue)
        else:
            n_iftrue = self.visit(c_ast.Compound([node.iftrue], coord=node.iftrue.coord))
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
        for_id = node_id(node.coord)
        # n_init = self.visit(node.init)
        n_init = self.visit(node.init if isinstance(node.init, c_ast.ExprList) else c_ast.ExprList([node.init], node.coord))                
        n_cond = self.visit(node.cond)
        # n_cond = self.visit(node.cond if isinstance(node.cond, c_ast.ExprList) else c_ast.ExprList([node.init], node.coord))        
        self.find_continue = False
        if not isinstance(node.stmt, c_ast.Compound):
            node.stmt = c_ast.Compound([node.stmt], node.stmt.coord)
        n_stmt = self.visit(node.stmt)
        if self.found_continue:
            self.found_continue = False
        n_next = self.visit(node.next)
        # We dont need to put a scope_info at the end of the for because the compound node already does that
        n_for = c_ast.For(n_init, n_cond, n_next, n_stmt, node.coord)
        return n_for

    def visit_While(self, node):
        #print('****************** Found While Node *******************')
        while_id = node_id(node.coord)
        n_cond = self.visit(node.cond)        
        # n_cond = self.visit(node.cond if isinstance(node.cond, c_ast.ExprList) else c_ast.ExprList([node.cond], node.coord))
        n_stmt = self.visit(node.stmt)
        n_while = c_ast.While(n_cond, n_stmt, node.coord)
        return n_while

    def visit_DoWhile(self, node):
        #print('****************** Found DoWhile Node *******************')
        while_id = node_id(node.coord)
        n_stmt = self.visit(node.stmt)
        n_cond = self.visit(node.cond)
        # n_cond = self.visit(node.cond if isinstance(node.cond, c_ast.ExprList) else c_ast.ExprList([node.cond], node.coord))                            
        n_while = c_ast.DoWhile(n_cond, n_stmt, node.coord)
        return n_while
    
    # def visit_Continue(self, node):
    #     # print('****************** Found Continue Node *******************')
    #     self.found_continue = True
    #     return node

    def visit_Enum(self, node):
        # print('****************** Found Enum Node *******************')        
        self.enums[node.name] = node.values
        return node

    def visit_Label(self, node):
        #print('****************** Found Label Node *******************')                
        #print(node.name)        
        node.stmt = self.visit(node.stmt)    
        return node

    def visit_Return(self, node):
        # print('****************** Found Return Node *******************')
        node.expr = self.visit(node.expr)        
        if self.next_label != None and self.curr_func_name == "main":
            if self.stmts_before_goto == None:
                if isinstance(node.expr, c_ast.Constant):
                    return c_ast.Goto(self.next_label, node.coord)
                else:
                    b = c_ast.Compound([node.expr, c_ast.Goto(self.next_label, node.coord)], node.coord)
                    return self.visit(b)
            else:
                b = deepcopy(self.stmts_before_goto)
                if not isinstance(node.expr, c_ast.Constant):
                     b.block_items.insert(0, node.expr)        
                b.block_items.append(c_ast.Goto(self.next_label, node.coord))                
                return self.visit(b)
        return node
    
    def visit_Typedef(self, node):
        # print('****************** Found Typedef Node *******************')                
        if node.name != "bool":
            return node

    def generic_visit(self, node):
        #print('******************  Something else ************')
        return node
        
def instrument_file(input_file, output_file, assertions, verbose):
    output_file, sincludes, includes = make_output_dir(input_file, output_file)#, logfilename, loglibpath)
    try:
        ast = parse_file(output_file, use_cpp=True,
            cpp_path='g++',
            cpp_args=['-E', '-Iutils/fake_libc_include'])
    except:
        print("Error while compiling:", input_file)
        return 0

    # print('******************** INPUT FILE: ********************')
    v = c_ast.NodeVisitor()
    v.visit(ast)
    # ast.show()
    v2 = FunctionInlineVisitor(args.verbose)
    ast = v2.visit(ast)    
    # exit()
    # v = VariablesVisitor()
    v = ProgramUnrollerVisitor(inputs, outputs, assertions, verbose)
    gen = c_generator.CGenerator()
    n_ast = v.visit(ast)
    # n_ast.show()
    gen_output_file(gen, n_ast, sincludes + includes, output_file)


def parser():
    parser = argparse.ArgumentParser(prog='program_unroller.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-na', '--no_assertions', action='store_true', default=False, help='No assertions will be injected onto each program scope.')
    parser.add_argument('-ip', '--inc_prog', help='Program to be repaired.')
    parser.add_argument('-cp', '--cor_prog', help='Correct program to be used by the repair process.')
    parser.add_argument('-m', '--var_map', help='Variable mapping, where each incorrect program\'s variable has a corresponding variable identifier of the correct program.')
    parser.add_argument('-md', '--var_map_dist', help='Path for the each variable mapping distheribution.')    
    parser.add_argument('-o', '--output_prog', nargs='?', help='Output program (program fixed).')
    parser.add_argument('-e', '--ipa', help='Name of the lab and exercise (IPA) so we can check the IO tests.')
    parser.add_argument('-t', '--test', help='Number of the IO test to use. If none, it will use all test in which the program does not return the expected output.', default="*")
    parser.add_argument('-td', '--test_dir', help='Test dir', default="C-Pack-IPAs/tests")
    parser.add_argument('--traces_dir', help='Traces dir. If none, the entire test suite of TCAS will be used.')                
    parser.add_argument('-upt', '--use_passed_tests', action='store_true', default=False, help='Unrolls the program also with the input and output values for passed tests.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args

if __name__ == '__main__':
    args = parser()
    # in_tests = glob.glob('{t_dir}/{d}/*_{t}.in'.format(t_dir=args.test_dir, d=args.ipa, t=args.test), recursive=True)
    # inputs = get_input_values(in_tests, args.inc_prog, only_failed_tests=not args.use_passed_tests)
    # out_tests = glob.glob('tests_updated/{d}/*_{t}.out'.format(d=args.ipa, t=args.test), recursive=True)     
    # outputs = get_output_values(out_tests, inputs)
    in_tests = glob.glob('C-Pack-IPAs/tests/{d}/*_{t}.in'.format(d=args.ipa, t=args.test) if args.test_dir == "C-Pack-IPAs/tests" or "tests_updated/"  else '{d}/tests/t{t}.in'.format(d=args.test_dir, t=args.test), recursive=True)
    inputs = get_input_values(in_tests, args.inc_prog, only_failed_tests=not args.use_passed_tests) if not args.traces_dir else get_input_values(in_tests, args.inc_prog, only_failed_tests=not args.use_passed_tests, tcas_traces=args.traces_dir)
    out_tests = glob.glob('tests_updated/{d}/*_{t}.out'.format(d=args.ipa, t=args.test) if args.test_dir == "C-Pack-IPAs/tests" or "tests_updated/" else '{d}/tests/t{t}.out'.format(d=args.test_dir, t=args.test) , recursive=True)
    outputs = get_output_values(out_tests, inputs)
    if args.verbose:
        print(inputs)
        print(outputs)
    instrument_file(args.inc_prog, args.output_prog, not args.no_assertions, args.verbose) 
    



