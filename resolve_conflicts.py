import os
import glob

def get_conflict_files():
    result = os.popen("git diff --name-only --diff-filter=U").read()
    return [x for x in result.split("\n") if x.strip()]

print("Conflict files:", get_conflict_files())
