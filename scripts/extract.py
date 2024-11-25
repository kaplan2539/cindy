#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import pathlib

bash_preamble = """#!/bin/bash

set -e
set -x
set -u

"""

r_include = re.compile(r"{{#include ([^:}]*)(:[0-9]*)?(:[0-9]*)?[^}]*}}([^{]*)")

def read_file(out,path,first_line=None,last_line=None):
    n=0
    with open(path,"rb") as f:
        for line in f:
            n+=1
            if first_line!=None and n<first_line:
               continue 
            if last_line!=None and n>last_line:
               break
            out.write(line)

def parse_code(f,out,input_path):
    n = 0
    for line in f:
        n+=1
        if line.startswith(b'```'):
            return
        cont=False
        for m in r_include.finditer(line.decode()):
            first = 1
            last = None
            filename = m.group(1)
            print(f"#DEBUG# line={line.decode()}")
            print(f"#DEBUG# g1=[{m.group(1)}]")
            print(f"#DEBUG# g2=[{m.group(2)}]")
            print(f"#DEBUG# g3=[{m.group(3)}]")
            print(f"#DEBUG# g4=[{m.group(4)}]")
            if(m.group(2)):
                try:
                    first = int(m.group(2)[1:])
                except:
                    pass
            if(m.group(3)):
                try:
                    last = int(m.group(3)[1:])
                except:
                    pass
            if not pathlib.Path(filename).is_absolute():
                print(f"## filename = {filename}")
                print(f"## input_path = {input_path}")
                filename = input_path / filename
            print(f"## filename = {filename}")
            read_file(out,filename,first,last)
            out.write(m.group(4).encode())
            cont=True
        if cont:
            continue
        out.write(line)

def main():
    parser = argparse.ArgumentParser(
        prog = "extract.py",
        description = "Extracs shell code from Markdown files",
        epilog = "Famous last words...",
    )

    parser.add_argument('input')
    parser.add_argument('output')
    args = parser.parse_args()

    input_path = pathlib.Path(args.input).parent
    print(f"input_path={input_path}")


    with open(args.input,"rb") as f, open(args.output,"wb") as out:
        out.write(bash_preamble.encode())
        n = 0
        for line in f:
            n += 1
#            print(f"{n}: {line}")
            if line.startswith(b'```shell') and not b'ignore' in line:
                parse_code(f,out,input_path)

if __name__ == "__main__":
    main()
