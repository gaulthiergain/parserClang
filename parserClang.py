#!/usr/bin/env python3
#---------------------------------------------------------------------
# (*) Installation:
#
# pip3 install clang
#
# On Linux:
#   cd /usr/lib/x86_64-linux-gnu/
#   sudo ln -s libclang-X.Y.so.1 libclang.so (X.Y the version number)
# 
# On Mac:
#   The clang library is by default set by the MAC_CLANG variable
#
# (*) Run:
#
# python3 parserClang.py <filepath> [includepathsfile]
#
# where filepath can be a repository/folder or a file (c/cpp/h/hpp)
#
#
# Gaulthier Gain <gaulthier.gain@uliege.be>
# License: BSD
#---------------------------------------------------------------------

import getopt
import os
import sys
import json
import clang.cindex
import clang
import argparse
import platform
from clang.cindex import CursorKind
from collections import defaultdict

MAC_CLANG = "/Applications/Xcode.app/Contents/Frameworks/libclang.dylib"

verbose = False # Change it to verbose mode
silent = False #

global_funcs = defaultdict(list)
global_calls = defaultdict(list)

# Check if a path is a directory or a file
def check_input_path(path, includePaths):
    if os.path.isdir(path):
        iterate_root_folder(path, includePaths)
    elif os.path.isfile(path):
        check_type_file(path, includePaths)
    else:
        sys.stderr("[WARNING] Unable to analyse this file: " + path)

def get_include_paths(rootdir, includepathsFile):
    paths = []
    with open(includepathsFile, 'r') as file:
        for includePath in file.readlines():
            path = '-isystem ' + rootdir + includePath.replace('\n', '')
            paths.append(path)

    return ' '.join(paths)

# Check type/extension of a given file
def check_type_file(filepath, includePaths):
    cplusplusOptions = '-x c++ --std=c++11'
    cOptions = ''

    if includePaths is not None:
        cplusplusOptions = cplusplusOptions + ' ' + includePaths
        cOptions = cOptions + ' ' + includePaths
    if not silent:
        print("Gathering symbols of " + filepath)
    
    if filepath.endswith(".cpp") or filepath.endswith(".hpp") or filepath.endswith(".cc"):
        parse_file(filepath, cplusplusOptions)
    elif filepath.endswith(".c") or filepath.endswith(".h") or filepath.endswith(".hh"):
        parse_file(filepath, cOptions)

# Iterate through a root folder
def iterate_root_folder(rootdir, includePaths):
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            filepath = subdir + os.sep + file
            check_type_file(filepath, includePaths)

# Print info about symbols (verbose mode)
def display_info_function(funcs, calls):
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
        print(list(tu.diagnostics))


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
        return displayname.split('(')[0]
    return displayname

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
            
            #increment counter
            if funcName not in global_calls:
                global_calls[funcName].append(1)
            else:
                global_calls[funcName][0] +=1

            #add path to file
            if c.location.file.name not in global_calls[funcName]:
                global_calls[funcName].append(c.location.file.name)

        elif c.kind == CursorKind.FUNCTION_DECL:
            funcs.append(c)
            # filter name to take only the name if necessary
            funcName = filter_func_name(c.displayname)
            
            #increment counter
            if funcName not in global_funcs:
                global_funcs[funcName].append(1)
            else:
                global_funcs[funcName][0] +=1

            #add path to file
            if c.location.file.name not in global_funcs[funcName]:
                global_funcs[funcName].append(c.location.file.name)

    return funcs, calls

# str2bool is used for boolean arguments parsing.
def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

# Write data to json file
def write_to_json(output_filename, data):
    with open(output_filename + '.json', 'w') as fp:
        json.dump(data, fp, indent=4, sort_keys=True)

# Open data to json file
def read_from_json(filename):
    with open(output_filename + '.json', 'r') as fp:
        data = json.load(fp)
    return data

# Read the list of syscalls (json file)
def read_syscalls_list(filename):
    with open(filename) as f:
        return json.load(f)


# Check which syscall is a function
def compare_syscalls(syscalls):
    if not silent:
        print("Gathered syscalls from function calls")

    called_syscalls = defaultdict(list)
    define_syscalls = defaultdict(list)

    for key, value in global_calls.items():
        if key in syscalls:
            if verbose:
                print(key, end=", ");
                print(global_calls[key])
            called_syscalls[key] = value

    for key, value in global_funcs.items():
        if key in syscalls:
            if verbose:
                print(key, end=", ");
                print(global_funcs[key])
            define_syscalls[key] = value
    
    return (called_syscalls, define_syscalls)

def main():
    global silent, verbose

    parser = argparse.ArgumentParser()

    parser.add_argument('--folder','-f', help='Path to the folder to analyse', required=True)
    parser.add_argument('--include','-i', help='Path to the includepathsFile')
    parser.add_argument('--output', '-o', help='Path to the output resulting json file', default="out.json")
    parser.add_argument('--syscalls','-s', help='Path to the syscalls file', default="syscalls.json")
    parser.add_argument('--verbose', '-v', type=str2bool, 
                        nargs='?', const=True, default=False,
                        help='Verbose mode')
    parser.add_argument('--silent', type=str2bool, 
                        nargs='?', const=True, default=False,
                        help='Display command (default=False)')
    args = parser.parse_args()

    verbose = args.verbose
    silent = args.silent

    if args.include is not None:
        includePaths = get_include_paths(args.folder, args.include)
        print(includePaths)
        check_input_path(args.folder, includePaths)
    else:
        check_input_path(args.folder, None)

    if not silent:
        print("---------------------------------------------------------")

    output_dict = {
            'functions':'',
            'calls':'',
            'called_syscalls':'',
            'define_syscalls':'',
        }
    output_dict['functions'] = [{'name':key, 'value':value} for key,value in global_funcs.items()]
    output_dict['calls'] = [{'name':key, 'value':value} for key,value in global_calls.items()]

    # Read syscalls from txt file
    syscalls = read_syscalls_list(args.syscalls)
    # Compare syscalls list with function declarations/calls
    (called_syscalls, define_syscalls) = compare_syscalls(syscalls)
    output_dict['called_syscalls'] = called_syscalls
    output_dict['define_syscalls'] = define_syscalls
        
    if args.output is None:
        output_file = sys.stdout
    else:
        output_file = open(args.output, "w")
        
    json.dump(output_dict, output_file, sort_keys=True, indent=4)


if __name__== "__main__":
    if platform.system() == "Darwin":
        clang.cindex.Config.set_library_file(MAC_CLANG)
    main()
