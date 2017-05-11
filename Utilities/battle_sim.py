#! usr/bin/env python2.7

w_mt = 5
w_acc = 90

class weapon(object):
	def __init__(self, mt, acc):
		self.mt = mt
		self.acc = acc

class player(object):
	def __init__(self, name, HP, STR, SKL, SPD, DEF):
		self.name = name
		self.hp = HP
		self.str = STR
		self.skl = SKL
		self.spd = SPD
		self.DEF = DEF

w = weapon(5, 90)
p1 = player("p1", 29, 10, 16, 17, 4)
p2 = player("p2", 29, 13, 16, 18, 7)

def damage(p1, p2, w):
	return max(0, p1.str+w.mt-p2.DEF)

def acc(p1, p2, w):
	return (min(100, max(0, p1.skl*2 + w.acc - p2.spd*2)))/100.0

winner = None
turn = False
while p1.hp > 0 and p2.hp > 0:
	print('Next Turn', p1.hp, p2.hp)
	turn = not turn
	if turn:
		p2.hp -= damage(p1, p2, w)*acc(p1, p2, w)
		print(p1.hp, p2.hp)
		if p2.hp < 0:
			winner = p1
			break
		else:
			p1.hp -= damage(p2, p1, w)*acc(p2, p1, w)
			print(p1.hp, p2.hp)
			if p1.hp < 0:
				winner = p2
				break
			elif p1.spd >= p2.spd + 4:
				p2.hp -= damage(p1, p2, w)*acc(p1, p2, w)
				print(p1.hp, p2.hp)
				if p2.hp < 0:
					winner = p1
					break
	else:
		p1.hp -= damage(p2, p1, w)*acc(p2, p1, w)
		print(p1.hp, p2.hp)
		if p1.hp < 0:
			winner = p2
			break
		else:
			p2.hp -= damage(p1, p2, w)*acc(p1, p2, w)
			print(p1.hp, p2.hp)
			if p2.hp < 0:
				winner = p1
				break
			elif p2.spd >= p1.spd + 4:
				p1.hp -= damage(p2, p1, w)*acc(p2, p1, w)
				print(p1.hp, p2.hp)
				if p1.hp < 0:
					winner = p2
					break

print(winner.name)





