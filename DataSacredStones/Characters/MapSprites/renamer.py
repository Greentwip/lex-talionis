import os

x = 'Warlock'
y = 'Druid'
for root, dirs, files in os.walk('.'):
    for name in files:
        full_name = os.path.join(root, name)
        if x in name:
            print(full_name)
            os.rename(full_name, os.path.join(root, name.replace(x, y)))
