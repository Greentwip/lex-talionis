import os

for root, dirs, files in os.walk('.'):
    for name in files:
        if name.endswith('.py'):
            continue
        klass, weapon, desc = name.split('-')
        if klass[-1] not in ('0', '5'):
            new_klass = klass + '0'
        else:
            new_klass = klass
        new_name = name.replace(klass, new_klass)
        full_name = os.path.join(root, name)
        print(full_name)
        new_name = full_name.replace(name, new_name)
        print(new_name)
        os.rename(full_name, new_name)