with open('Explosion-Index.txt') as fp:
	lines = fp.readlines()

with open('new_index.txt', 'w') as fp:
	for line in lines:
		s_l = line.split(';')
		x, y = s_l[1].split(',')
		width, height = s_l[2].split(',')
		offset_x, offset_y = s_l[3].split(',')

		# place on other side
		offset_x = 240 - int(offset_x) - int(width)

		fp.write(line.replace(s_l[3], str(offset_x) + ',' + offset_y))



