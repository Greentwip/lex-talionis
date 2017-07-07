import glob

for fp in glob.glob('*.py'):
    print('=== %s ===' %fp)
    import_dict = {}
    getting_imports = True
    next_line = False
    with open(fp) as script:
        lines = [line.strip() for line in script.readlines()]
    for line in lines:
        if getting_imports:
            if next_line:
                next_line = False
                s_l = line.split(',')
                for pull in s_l:
                    pull = pull.strip()
                    if pull == "\\":
                        next_line = True
                    import_dict[pull.strip()] = False
            elif line.startswith('import'):
                s_l = line[6:].split(',')
                for pull in s_l:
                    pull = pull.strip()
                    if pull == "\\":
                        next_line = True
                    import_dict[pull.strip()] = False
            elif line.startswith('from'):
                s_l = line.split()
                pull = s_l[3:]
                for i in pull:
                    if ',' in i:
                        i = i[:-1]
                    if i != '*':
                        import_dict[i] = False
            elif not line:
                pass
            elif line.startswith('#'):
                pass
            else:
                getting_imports = False
        else:
            for key in import_dict:
                if key in line:
                    import_dict[key] = True
    for key, value in import_dict.iteritems():
        if value:
            print('%s: Found'%key)
        else:
            print('%s: Missing'%key)

            
