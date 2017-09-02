import glob

for fp in glob.glob('*-Index.txt'):
    with open(fp) as index_file:
        lines = [l.strip().split(';') for l in index_file.readlines()]

    with open(fp, 'w') as index_script:
        for line in lines:
            name, pos, size, offset = line
            x, y = [int(n) for n in pos.split(',')]
            width, height = [int(n) for n in size.split(',')]
            offset_x, offset_y = [int(n) for n in offset.split(',')]
            offset_x -= 4
            index_script.write(name + ';' + str(x) + ',' + str(y) + ';' + str(width) + ',' + str(height) + ';' + str(offset_x) + ',' + str(offset_y) + '\n')
