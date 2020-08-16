# Calculations.py
import re

class Parser(object):
    def __init__(self, fn):
        with open(fn, mode='r', encoding='utf-8') as fp:
            lines = [line.strip() for line in fp.readlines() if not line.startswith('#')]
        stat_line = lines[0]
        # equations = [l.replace(" ", "") for l in lines[1:]]
        equations = [l for l in lines[1:]]

        self.stat_list = ['HP'] + stat_line.split(';') + ['MOV']
        assert len(set(self.stat_list)) == len(self.stat_list)

        self.equations = {}
        for line in equations:
            if '=' not in line:
                print('%s is not a valid combat equation' % line)
                continue
            lhs, rhs = line.split('=')
            lhs = lhs.strip()
            self.equations[lhs] = self.tokenize(rhs)

        self.replacement_dict = self.create_replacement_dict()
        for lhs in list(self.equations.keys()):
            self.fix(lhs, self.replacement_dict)

    def tokenize(self, s):
        return re.split('([^a-zA-Z_])', s)

    def create_replacement_dict(self):
        dic = {}
        for stat in self.stat_list:
            dic[stat] = ("unit.stats['%s']" % stat)
        for lhs in self.equations.keys():
            dic[lhs] = ("equations['%s'](equations, unit, item, dist)" % lhs)
        dic['WEIGHT'] = '(item.weight if item and item.weight else 0)'
        dic['DIST'] = 'dist'
        return dic

    def fix(self, lhs, dic):
        rhs = self.equations[lhs]
        rhs = [dic.get(n, n) for n in rhs]
        rhs = ''.join(rhs)
        rhs = 'int(%s)' % rhs
        exec("def %s(equations, unit, item=None, dist=0): return %s" % (lhs, rhs), self.equations)
        # self.equations[lhs] = rhs

    def get_attackspeed(self, unit, item=None, dist=0):
        return self.equations['AS'](self.equations, unit, item, dist)

    def get_hit(self, unit, item=None, dist=0):
        return self.equations['HIT'](self.equations, unit, item, dist)

    def get_avoid(self, unit, item=None, dist=0):
        return self.equations['AVOID'](self.equations, unit, item, dist)

    def get_crit(self, unit, item=None, dist=0):
        return self.equations['CRIT'](self.equations, unit, item, dist)

    def get_crit_avoid(self, unit, item=None, dist=0):
        return self.equations['CRIT_AVOID'](self.equations, unit, item, dist)

    def get_damage(self, unit, item=None, dist=0):
        return self.equations['DAMAGE'](self.equations, unit, item, dist)

    def get_defense(self, unit, item=None, dist=0):
        return self.equations['DEFENSE'](self.equations, unit, item, dist)

    def get_magic_damage(self, unit, item=None, dist=0):
        return self.equations['MAGIC_DAMAGE'](self.equations, unit, item, dist)

    def get_magic_defense(self, unit, item=None, dist=0):
        return self.equations['MAGIC_DEFENSE'](self.equations, unit, item, dist)

    def get_rating(self, unit, item=None, dist=0):
        return self.equations['RATING'](self.equations, unit, item, dist)

    def get_aid(self, unit, item=None, dist=0):
        return self.equations['RESCUE_AID'](self.equations, unit, item, dist)

    def get_weight(self, unit, item=None, dist=0):
        return self.equations['RESCUE_WEIGHT'](self.equations, unit, item, dist)

    def get_steal_atk(self, unit, item=None, dist=0):
        return self.equations['STEAL_ATK'](self.equations, unit, item, dist)

    def get_steal_def(self, unit, item=None, dist=0):
        return self.equations['STEAL_DEF'](self.equations, unit, item, dist)

    def get_heal(self, unit, item=None, dist=0):
        return self.equations['HEAL'](self.equations, unit, item, dist)

    def get_max_fatigue(self, unit, item=None, dist=0):
        return self.equations['MAX_FATIGUE'](self.equations, unit, item, dist)

    def get_equation(self, lhs, unit, item=None, dist=0):
        return self.equations[lhs](self.equations, unit, item, dist)

    def get_expression(self, expr, unit, item=None, dist=0):
        expr = self.tokenize(expr)
        expr = [self.replacement_dict.get(n, n) for n in expr]
        expr = ''.join(expr)
        expr = 'int(%s)' % expr
        equations = self.equations
        return eval(expr)
