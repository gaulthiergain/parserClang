# parserClang
A very basic C parser to extract functions from C/Cpp source files. This is a prototype (no solid error handling, modular code, etc).

## Installation

Run the following commands:

```
pip3 install clang 
cd /usr/lib/x86_64-linux-gnu/
sudo ln -s libclang-X.Y.so.1 libclang.so (X.Y the version number)
```

## Run

```
python3 parserClang.py [-i includePaths] [-o outputfile] -[qv] inputfile.c [otherinputfile.c ...]
```

where filepath can be a repository/folder or a file (c/cpp/h/hpp)
