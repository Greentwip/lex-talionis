#! usr/bin/env python
import os

for root, dirs, files in os.walk('.'):
    for name in files:
        print(name)
        full_name = os.path.join(root, name)
        if name.startswith('Enemy'):
            os.rename(full_name, full_name.replace('Enemy', 'enemy'))
        elif name.startswith('Other'):
            os.rename(full_name, full_name.replace('Other', 'other'))
        elif not name.startswith('Generic'):
            os.rename(full_name, full_name.replace(name, 'player' + name))
        