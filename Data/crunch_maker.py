### Unit Info
with open('units.xml') as fp:
	lines = fp.readlines()

new_lines = [line.strip() for line in lines]
for index, line in enumerate(new_lines):
	if line.startswith('<bases>'):
		s_l = [float(num) for num in line[7:-8].split(',')]
		s_l = [int(round(num*2/3)) for num in s_l]
		lines[index] = '\t\t<bases>' + ','.join([str(num) for num in s_l]) + '</bases>\n'
	elif line.startswith('<growths>'):
		s_l = [float(num) for num in line[9:-10].split(',')]
		# If all the growths are divisible by 50, just ignore it.
		if not any((int(num))%50 for num in s_l):
			continue
		s_l = [int(round((num/5)*2/3))*5 for num in s_l]
		lines[index] = '\t\t<growths>' + ','.join([str(num) for num in s_l]) + '</growths>\n'

with open('new_units.xml', 'w') as new_fp:
	for line in lines:
		new_fp.write(line)

### Class Info
with open('class_info.xml') as fp:
	lines = fp.readlines()

new_lines = [line.strip() for line in lines]
for index, line in enumerate(new_lines):
	if line.startswith('<bases>'):
		s_l = [float(num) for num in line[7:-8].split(',')]
		s_l = [int(round(num*2/3)) for num in s_l]
		lines[index] = '\t\t<bases>' + ','.join([str(num) for num in s_l]) + '</bases>\n'
	elif line.startswith('<growths>'):
		s_l = [float(num) for num in line[9:-10].split(',')]
		s_l = [int(round((num/5)*2/3))*5 for num in s_l]
		lines[index] = '\t\t<growths>' + ','.join([str(num) for num in s_l]) + '</growths>\n'
	elif line.startswith('<max>'):
		s_l = [float(num) for num in line[5:-6].split(',')]
		s_l = [max(15, int(round(num*2/3))) for num in s_l]
		lines[index] = '\t\t<max>' + ','.join([str(num) for num in s_l[:-1]]) + ',20</max>\n'

with open('new_class_info.xml', 'w') as new_fp:
	for line in lines:
		new_fp.write(line)

### Item Info
with open('items.xml') as fp:
	lines = fp.readlines()

new_lines = [line.strip() for line in lines]
for index, line in enumerate(new_lines):
	if line.startswith('<WT>'):
		s_l = float(line[4:-5])
		s_l = int(round(s_l*2/3))
		lines[index] = '\t\t<WT>' + str(s_l) + '</WT>\n'
	elif line.startswith('<MT>'):
		s_l = float(line[4:-5])
		s_l = int(round(s_l*2/3))
		lines[index] = '\t\t<MT>' + str(s_l) + '</MT>\n'
	elif line.startswith('<damage>'):
		s_l = float(line[8:-9])
		s_l = int(round(s_l*2/3))
		lines[index] = '\t\t<damage>' + str(s_l) + '</damage>\n'

with open('new_items.xml', 'w') as new_fp:
	for line in lines:
		new_fp.write(line)