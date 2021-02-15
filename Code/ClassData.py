from collections import OrderedDict

# Custom imports
from . import GlobalConstants as GC
from . import configuration as cf
from . import Utility, Weapons

# === PARSES A SKILL LINE =====================================================
def class_skill_parser(skill_text):
    if skill_text is not None:
        each_skill = skill_text.split(';')
        split_line = [(int(skill.split(',')[0]), skill.split(',')[1]) for skill in each_skill]
        return split_line
    else:
        return []

def create_class_dict():
    class_dict = OrderedDict()
    # For each class
    for klass in GC.CLASSDATA.getroot().findall('class'):
        c_id = klass.get('id')
        tier = int(klass.find('tier').text)
        wexp_gain = klass.find('wexp_gain').text.split(',')
        for index, wexp in enumerate(wexp_gain[:]):
            if wexp in Weapons.EXP.wexp_dict:
                wexp_gain[index] = Weapons.EXP.wexp_dict[wexp]
        wexp_gain = [int(num) for num in wexp_gain]
        class_dict[c_id] = {'short_name': klass.find('short_name').text,
                            'long_name': klass.find('long_name').text,
                            'id': c_id,
                            'tier': tier,
                            'wexp_gain': wexp_gain,
                            'promotes_from': klass.find('promotes_from').text if klass.find('promotes_from') is not None else None,
                            'turns_into': klass.find('turns_into').text.split(',') if klass.find('turns_into').text is not None else [],
                            'movement_group': int(klass.find('movement_group').text),
                            'tags': set(klass.find('tags').text.split(',')) if klass.find('tags').text is not None else set(),
                            'skills': class_skill_parser(klass.find('skills').text),
                            'growths': Utility.intify_comma_list(klass.find('growths').text),
                            'bases': Utility.intify_comma_list(klass.find('bases').text),
                            'promotion': Utility.intify_comma_list(klass.find('promotion').text) if klass.find('promotion') is not None else [0]*10,
                            'max': Utility.intify_comma_list(klass.find('max').text) if klass.find('max') is not None else [60],
                            'desc': (klass.find('desc').text or '') if klass.find('desc') is not None else '',
                            'exp_multiplier': float(klass.find('exp_multiplier').text) if klass.find('exp_multiplier') is not None else 1.,
                            'exp_when_attacked': float(klass.find('exp_when_attacked').text) if klass.find('exp_when_attacked') is not None else 1.,
                            'max_level': int(klass.find('max_level').text) if klass.find('max_level') is not None else Utility.find_max_level(tier, cf.CONSTANTS['max_level'])}
        class_dict[c_id]['bases'].extend([0] * (cf.CONSTANTS['num_stats'] - len(class_dict[c_id]['bases'])))
        class_dict[c_id]['growths'].extend([0] * (cf.CONSTANTS['num_stats'] - len(class_dict[c_id]['growths'])))
        class_dict[c_id]['max'].extend([cf.CONSTANTS['max_stat']] * (cf.CONSTANTS['num_stats'] - len(class_dict[c_id]['max'])))
    return class_dict

class_dict = create_class_dict()
