# Average Stat Calculator
import collections
# DATA
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

loc = '../../'

CLASSDATA = ET.parse(loc + 'Data/class_info.xml')
UNITDATA = ET.parse(loc + 'Data/units.xml')
num_stats = 10
max_stat = 20

def intify_comma_list(comma_string):
    # Takes string, turns it into list of ints
    if comma_string:
        s_l = comma_string.split(',')
        s_l = [int(num) for num in s_l]
    else:
        s_l = []
    return s_l

# === CREATE CLASS DICTIONARY ================================================
def create_class_dict():
    class_dict = collections.OrderedDict()
    # For each class
    for klass in CLASSDATA.getroot().findall('class'):
        name = klass.get('id')
        class_dict[name] = {'name': klass.find('name').text,
                            'tier': klass.find('tier').text,
                            'wexp_gain': intify_comma_list(klass.find('wexp_gain').text),
                            'promotes_from': klass.find('promotes_from').text.split(',') if klass.find('promotes_from').text is not None else [],
                            'turns_into': klass.find('turns_into').text.split(',') if klass.find('turns_into').text is not None else [],
                            'movement_group': int(klass.find('movement_group').text),
                            'tags': klass.find('tags').text,
                            'growths': intify_comma_list(klass.find('growths').text),
                            'bases': intify_comma_list(klass.find('bases').text),
                            'promotion': intify_comma_list(klass.find('promotion').text) if klass.find('promotion') is not None else [0]*10,
                            'max': intify_comma_list(klass.find('max').text) if klass.find('max') is not None else [60],
                            'desc': klass.find('desc').text}
        class_dict[name]['bases'].extend([0] * (num_stats - len(class_dict[name]['bases'])))
        class_dict[name]['growths'].extend([0] * (num_stats - len(class_dict[name]['growths'])))
        class_dict[name]['promotion'].extend([0] * (num_stats - len(class_dict[name]['promotion'])))
        class_dict[name]['max'].extend([max_stat] * (num_stats - len(class_dict[name]['max'])))
    return class_dict

class_dict = create_class_dict()

def get_stats(klass, level):
    stats = []
    if level <= 10:
        for i in xrange(num_stats):
            stat = int(klass['bases'][i] + klass['growths'][i]/100.*(level - 1) + .5)
            stat = min(stat, klass['max'][i])
            stats.append(stat)
    else:
        for i in xrange(num_stats):
            stat = int(klass['bases'][i] + klass['growths'][i]/100.*(level - 2) + .5)
            stat = min(stat, klass['max'][i])
            stats.append(stat)
    return stats

fp = open('class_stat_overview.csv', 'w')
for name, klass in class_dict.iteritems():
    fp.write(name + '\n')
    if klass['tier'] == '1':
        final_stats = get_stats(klass, 10)
        final_stats = sum(final_stats) - min(final_stats[1], final_stats[2])
    else:
        final_stats = get_stats(klass, 20)
        final_stats = sum(final_stats) - min(final_stats[1], final_stats[2])
    fp.write(str(final_stats) + ',HP,STR,MAG,SKL,SPD,LCK,DEF,RES,CON,MOV' + '\n')
    fp.write('BASE,' + ','.join([str(i) for i in klass['bases']]) + '\n')
    fp.write('GROWTHS,' + ','.join([str(i) for i in klass['growths']]) + '\n')
    if klass['tier'] == '1':
        fp.write('1,' + ','.join([str(i) for i in get_stats(klass, 1)]) + '\n')
        fp.write('5,' + ','.join([str(i) for i in get_stats(klass, 5)]) + '\n')
        fp.write('10,' + ','.join([str(i) for i in get_stats(klass, 10)]) + '\n')
    else:
        fp.write('11,' + ','.join([str(i) for i in get_stats(klass, 11)]) + '\n')
        fp.write('15,' + ','.join([str(i) for i in get_stats(klass, 15)]) + '\n')
        fp.write('20,' + ','.join([str(i) for i in get_stats(klass, 20)]) + '\n')
    fp.write('\n')
    if any(num != 0 for num in klass['promotion']):
        fp.write('PROMOTE,' + ','.join([str(i) for i in klass['promotion']]) + ',' + str(sum(klass['promotion'])) + '\n')
        fp.write('CAPS,' + ','.join([str(i) for i in klass['max']]) + '\n')
        fp.write('\n')
fp.close()

def get_unit_stats(klass, bases, growths, level, base_level):
    stats = []
    if level <= 10:
        for i in xrange(num_stats):
            stat = int(bases[i] + growths[i]/100.*(level - base_level) + .5)
            stat = min(stat, klass['max'][i])
            stats.append(stat)
    else:
        if klass['turns_into']:
            new_klass = class_dict[klass['turns_into'][0]]
        else:
            new_klass = klass
        for i in xrange(num_stats):
            orig_stat = bases[i] + growths[i]/100.*(10 - base_level) + .5
            orig_stat = min(orig_stat, klass['max'][i])
            stat = int(orig_stat + growths[i]/100.*(level - 11) + new_klass['promotion'][i])
            stat = min(stat, new_klass['max'][i])
            stats.append(stat)
    return stats

fp = open('unit_stat_overview.csv', 'w')
for unit in UNITDATA.getroot().findall('unit'):
    base_level = int(unit.find('level').text)
    classes = unit.find('class').text.split(',')
    klass = class_dict[classes[-1]]
    bases = intify_comma_list(unit.find('bases').text)
    for n in xrange(len(bases), num_stats):
        bases.append(klass['bases'][n])
    growths = intify_comma_list(unit.find('growths').text)
    growths.extend([0] * (num_stats - len(growths)))
    final_stats = get_unit_stats(klass, bases, growths, 20, base_level)
    final_stats = sum(final_stats) - min(final_stats[1], final_stats[2])
    fp.write(unit.get('name') + ',,' + str(base_level) + ',,' + str(sum(bases)) + ',,' + str(sum(growths)) + '\n')
    fp.write(str(final_stats) + ',HP,STR,MAG,SKL,SPD,LCK,DEF,RES,CON,MOV' + '\n')
    fp.write('BASE,' + ','.join([str(i) for i in bases]) + '\n')
    fp.write('GROWTHS,' + ','.join([str(i) for i in growths]) + '\n')
    fp.write('1,' + ','.join([str(i) for i in get_unit_stats(klass, bases, growths, 1, base_level)]) + '\n')
    fp.write('5,' + ','.join([str(i) for i in get_unit_stats(klass, bases, growths, 5, base_level)]) + '\n')
    fp.write('10,' + ','.join([str(i) for i in get_unit_stats(klass, bases, growths, 10, base_level)]) + '\n')
    fp.write('11,' + ','.join([str(i) for i in get_unit_stats(klass, bases, growths, 11, base_level)]) + '\n')
    fp.write('15,' + ','.join([str(i) for i in get_unit_stats(klass, bases, growths, 15, base_level)]) + '\n')
    fp.write('20,' + ','.join([str(i) for i in get_unit_stats(klass, bases, growths, 20, base_level)]) + '\n')
    fp.write('\n')
    if klass['turns_into']:
        new_klass = class_dict[klass['turns_into'][0]]
    else:
        new_klass = klass
    fp.write('PROMOTE,' + ','.join([str(i) for i in new_klass['promotion']]) + ',' + str(sum(new_klass['promotion'])) + '\n')
    fp.write('CAPS,' + ','.join([str(i) for i in new_klass['max']]) + '\n')
    fp.write('\n')
fp.close()
