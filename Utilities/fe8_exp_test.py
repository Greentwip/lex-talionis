mlevel = 1
elevel = 1
mclass_bonus_a = 20
eclass_bonus_a = 0
mclass_bonus_b = 60
eclass_bonus_b = 0
mclass_power = 3
eclass_power = 2

def damage_exp():
    return (31 + elevel + eclass_bonus_a - mlevel - mclass_bonus_a) / mclass_power

def defeat_exp(mode=1):
    return (elevel * eclass_power + eclass_bonus_b) - ((mlevel * mclass_power + mclass_bonus_b) / mode)

def kill_exp():
    return damage_exp() + max(0, 20 + (defeat_exp() if defeat_exp() > 0 else defeat_exp(2)))

print(damage_exp())
print(defeat_exp())
print(defeat_exp(2))
print(kill_exp())
