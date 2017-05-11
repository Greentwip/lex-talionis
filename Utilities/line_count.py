# Line counter

import os

def file_len(fname):
    i = -1
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

print(sum(file_len(fp) for fp in os.listdir('.')))