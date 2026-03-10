import os
import subprocess

files = subprocess.check_output(["git", "diff", "--name-only", "--diff-filter=U"]).decode("utf-8").split("\n")
files = [f for f in files if f]

for f in files:
    print(f"\n--- {f} ---")
    with open(f, "r") as fd:
        content = fd.read()
    
    lines = content.split('\n')
    in_conflict = False
    for i, line in enumerate(lines):
        if line.startswith("<<<<<<< "):
            in_conflict = True
            print(f"L{i}: {line}")
        elif line.startswith("======="):
            print(f"L{i}: {line}")
        elif line.startswith(">>>>>>> "):
            print(f"L{i}: {line}")
            in_conflict = False
        elif in_conflict:
            print(f"L{i}: {line}")

