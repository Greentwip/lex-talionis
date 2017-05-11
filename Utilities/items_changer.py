with open('items.xml') as fp:
	lines = fp.readlines()

my_lines = []

import textwrap

found = False
for line in lines:
	if line.strip().startswith('<stats>'):
		found = True
	elif line.strip().startswith('</stats>'):
		found = False
	elif found:
		my_lines.append('\t\t' + textwrap.dedent(line))
	else:
		my_lines.append(line)

with open('new_items.xml', 'w') as fp:
	for line in my_lines:
		fp.write(line)