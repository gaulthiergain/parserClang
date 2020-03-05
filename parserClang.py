#!/usr/bin/env python3
#---------------------------------------------------------------------
# (*) Installation:
#
# pip3 install clang
# 
# cd /usr/lib/x86_64-linux-gnu/
# sudo ln -s libclang-X.Y.so.1 libclang.so (X.Y the version number)
#
# (*) Run:
#
# python3 parserClang.py <filepath>
# 
# where filepath can be a repository/folder or a file (c/cpp/h/hpp)
#
#
# Gaulthier Gain <gaulthier.gain@uliege.be>
# License: BSD
#---------------------------------------------------------------------

import os
import sys
import json
import clang.cindex
from clang.cindex import CursorKind
from collections import Counter

verbose = False # Change it to verbose mode

global_funcs = Counter()
global_calls = Counter()

# Check if a path is a directory or a file
def check_input_path(path):
    if os.path.isdir(path):  
        iterate_root_folder(path)
    elif os.path.isfile(path):  
        check_type_file(path)
    else:
        print("Unable to analyse this file")

# Check type/exenstion of a given file
def check_type_file(filepath):
    if filepath.endswith(".cpp") or filepath.endswith(".hpp"):
        print("Gathering symbols of " + filepath) 
        parse_file(filepath, '-x c++ --std=c++11')
    elif filepath.endswith(".c") or filepath.endswith(".h"):
        print("Gathering symbols of " + filepath) 
        parse_file(filepath, '')

# Iterate through a root folder
def iterate_root_folder(rootdir):
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            filepath = subdir + os.sep + file
            check_type_file(filepath)

# Print info about symbols (verbose mode)
def display_info_function(funcs, calls):
    print("------------------------------------------------------")
    for f in funcs:
        print(fully_qualified(f), f.location)
        for c in calls:
            if is_function_call(f, c):
                print('-', c.location)
        print()

# Parse a given file to generate a AST
def parse_file(filepath, arguments):

    idx = clang.cindex.Index.create()
    args = arguments.split()
    tu = idx.parse(filepath, args=args)
    funcs, calls = find_funcs_and_calls(tu)
    if verbose:
        display_info_function(funcs, calls)
        
# Retrieve a fully qualified function name (with namespaces)
def fully_qualified(c):
    if c is None:
        return ''
    elif c.kind == CursorKind.TRANSLATION_UNIT:
        return ''
    else:
        res = fully_qualified(c.semantic_parent)
        if res != '':
            return res + '::' + c.spelling
    return c.spelling

# Determine where a call-expression cursor refers to a particular
# function declaration
def is_function_call(funcdecl, c):
    defn = c.get_definition()
    return (defn is not None) and (defn == funcdecl)

# Filter name to take only the function name (remove "(args)")
def filter_func_name(displayname):
    if "(" in displayname:
        funcName = displayname.split('(')[0]
    else:
        funcName = displayname
    return funcName

# Retrieve lists of function declarations and call expressions in a
#translation unit
def find_funcs_and_calls(tu):
    filename = tu.cursor.spelling
    calls = []
    funcs = []
    for c in tu.cursor.walk_preorder():
        if c.location.file is None:
            pass
        elif c.location.file.name != filename:
            pass
        elif c.kind == CursorKind.CALL_EXPR:
            calls.append(c)
            # filter name to take only the name if necessary
            funcName = filter_func_name(c.displayname)
            global_calls[funcName] += 1
        elif c.kind == CursorKind.FUNCTION_DECL:
            funcs.append(c)
            # filter name to take only the name if necessary
            funcName = filter_func_name(c.displayname)
            global_funcs[funcName] += 1
    return funcs, calls

# Write data to json file
def write_to_json(output_filename, data):
    with open(output_filename + '.json', 'w') as fp:
        json.dump(data, fp, indent=4, sort_keys=True)

# Open data to json file
def read_from_json(filename):
    with open(output_filename + '.json', 'r') as fp:
        data = json.load(fp)
    return data

# Read the list of syscalls (text file)
def read_syscalls_list(filename):
    syscalls = set()
    with open(filename) as f:
        for line in f:
            syscalls.add(line.strip())
    return syscalls

# Check which syscall is called
def compare_syscalls(syscalls):

    print("---------------------------------------------------------")
    print("Syscalls from function calls:")
    print("---------------------------------------------------------")

    for key in global_calls.keys():
        if key in syscalls:
            print(key)

# Main function
def main():

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        print("Filename must be specified: python3 parserClang.py <filepath>")
        exit(1)

    check_input_path(filepath)

    print("---------------------------------------------------------")

    # Dump function declarations to json
    result = [{'name':key, 'value':value} for key,value in global_funcs.items()]
    write_to_json("functions_", result) 
    print("Frequency of functions written to functions_.json")

    # Dump function calls to json
    result = [{'name':key, 'value':value} for key,value in global_calls.items()]
    write_to_json("calls_", result) 
    print("Frequency of calls written to calls_.json")

    # Read syscalls from txt file
    syscalls = read_syscalls_list('syscall_list.txt')

    # Compare syscalls list with function declarations/calls
    compare_syscalls(syscalls)

if __name__== "__main__":
  
    main()