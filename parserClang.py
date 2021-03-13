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
import platform
from clang.cindex import CursorKind
from collections import Counter

MAC_CLANG = "/Applications/Xcode.app/Contents/Frameworks/libclang.dylib"

verbose = False # Change it to verbose mode

global_funcs = Counter()
global_calls = Counter()

silent_flag = False

# Check if a path is a directory or a file
def check_input_path(path, includePaths):
    if os.path.isdir(path):
        iterate_root_folder(path, includePaths)
    elif os.path.isfile(path):
        check_type_file(path, includePaths)
    else:
        print("Unable to analyse this file")
        exit(1)

def get_include_paths(rootdir, includepathsFile):
    paths = []
    with open(includepathsFile, 'r') as file:
        for includePath in file.readlines():
            path = '-isystem ' + rootdir + includePath.replace('\n', '')
            paths.append(path)

    return ' '.join(paths)

# Check type/exenstion of a given file
def check_type_file(filepath, includePaths):
    cplusplusOptions = '-x c++ --std=c++11'
    cOptions = ''

    if includePaths is not None:
        cplusplusOptions = cplusplusOptions + ' ' + includePaths
        cOptions = cOptions + ' ' + includePaths
    if silent_flag is False:
        print("Gathering symbols of " + filepath)
    if filepath.endswith(".cpp") or filepath.endswith(".hpp"):
        parse_file(filepath, cplusplusOptions)
    elif filepath.endswith(".c") or filepath.endswith(".h"):
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
    if silent_flag is False:
        print("Gathered syscalls from function calls:")

    return [key for key in global_calls.keys() if key not in syscalls]



# Main function
def main():
    optlist, args = getopt.getopt(sys.argv[1:], "o:qvt")
    input_file_names = None
    includepathsFile = None
    output_file_name = None
    textFormat = False
    for opt in optlist:
        if opt[0] == "-i":
            includepathFile = opt[1]
        if opt[0] == "-o":
            output_file_name = opt[1]
        if opt[0] == "-q":
            global silent_flag
            silent_flag = True
        if opt[0] == "-v":
            global verbose
            verbose = True
        if opt[0] == "-t":
            textFormat = True

    input_file_names = args
    if len(input_file_names) == 0:
        if silent_flag is False:
            print("No input files supplied")
        exit(1)
    if includepathsFile is not None:
        includePaths = get_include_paths(input_file_name, includepathsFile)
        for input_file_name in input_file_names:
            check_input_path(input_file_name, includePaths)
    else:
        for input_file_name in input_file_names:
            check_input_path(input_file_name, None)

    if silent_flag is False:
        print("---------------------------------------------------------")

    if textFormat:
        i = 0
        for key,value in global_funcs.items():
            if i < len(global_funcs.items())-1:
                print(key, end=',')
            else:
                print(key)
            i = i + 1
    else:
        # Dump function declarations and calls to json
        output_dikt = {
            'functions':'',
            'calls':''
        }
        output_dikt['functions'] = [{'name':key, 'value':value} for key,value in global_funcs.items()]
        output_dikt['calls'] = [{'name':key, 'value':value} for key,value in global_calls.items()]
        if includepathsFile is not None:
            # Read syscalls from txt file
            all_syscalls = read_syscalls_list('syscall_list.txt')
            called_syscalls = compare_syscalls(all_syscalls)
            output_dikt['syscalls'] = called_syscalls
        if output_file_name is None:
            output_file = sys.stdout
        else:
            output_file = open(output_file_name, "w")
        json.dump(output_dikt, output_file)


if __name__== "__main__":
    if platform.system() == "Darwin":
        clang.cindex.Config.set_library_file(MAC_CLANG)
    main()
