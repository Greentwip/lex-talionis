# === Imports ==================================================================
# Custom imports
try:
    import GlobalConstants as GC
    import configuration as cf
    import static_random
    import CustomObjects, ActiveSkill, Interaction, InfoMenu
    import Aura, Action, Utility, Engine
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import static_random
    from . import CustomObjects, ActiveSkill, Interaction, InfoMenu
    from . import Aura, Action, Utility, Engine

import logging
logger = logging.getLogger(__name__)

# === New Status Object ========================================================
class Status(object):
    next_uid = 100

    def __init__(self, s_id, name, components, desc, image_index=None):
        self.uid = Status.next_uid
        Status.next_uid += 1
        self.id = s_id
        self.name = name
        self.desc = desc
        self.image_index = image_index or (0, 0)
        self.owner_id = None  # Like item_owner but for statuses
        self.giver_id = None  # Who created/gave away this status
        self.data = {}  # Stores persistent data that needs to be kept across saves

        self.children = set()

        # Creates component slots
        self.components = components # Consumable, Weapon, Spell Bigger Picture
        for component_key, component_value in self.components.items():
            self.__dict__[component_key] = component_value

        self.loadSprites()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def add_child(self, child):
        self.children.add(child)

    def remove_child(self, child):
        self.children.discard(child)

    def removeSprites(self):
        self.image = None
        self.cooldown = None
        if self.upkeep_animation:
            self.upkeep_animation.removeSprites()
        if self.always_animation:
            self.always_animation.removeSprites()
        if self.activated_item and self.activated_item.item:
            self.activated_item.item.removeSprites()

    def loadSprites(self):
        self.image = Engine.subsurface(GC.ITEMDICT['Skills'], (16*self.image_index[0], 16*self.image_index[1], 16, 16)) if self.image_index else None
        self.cooldown = GC.IMAGESDICT['IconCooldown']
        if self.upkeep_animation:
            self.upkeep_animation.loadSprites()
        if self.always_animation:
            self.always_animation.loadSprites()
        if self.activated_item and self.activated_item.item:
            self.activated_item.item.loadSprites()
        self.help_box = None

    def serialize(self):
        serial_dict = {}
        serial_dict['uid'] = self.uid
        serial_dict['id'] = self.id
        serial_dict['time_left'] = self.time.time_left if self.time else None
        serial_dict['upkeep_sc_count'] = self.upkeep_stat_change.count if self.upkeep_stat_change else None
        # serial_dict['active_charge'] = self.active.current_charge if self.active else None
        # serial_dict['automatic_charge'] = self.automatic.current_charge if self.automatic else None
        if self.activated_item:
            self.data['activated_item'] = self.activated_item.current_charge
        elif self.combat_art:
            self.data['combat_art'] = self.combat_art.current_charge
        serial_dict['children'] = self.children
        serial_dict['owner_id'] = self.owner_id
        serial_dict['giver_id'] = self.giver_id
        # serial_dict['count'] = self.count.count if self.count else None
        serial_dict['stat_halve_penalties'] = self.stat_halve.penalties if self.stat_halve else None
        serial_dict['aura_child_uid'] = self.aura.child_status.uid if self.aura else None
        serial_dict['data'] = self.data
        return serial_dict

    def draw(self, surf, topleft, cooldown=True):
        if self.image:
            surf.blit(self.image, topleft)

        # Cooldown
        if cooldown:
            if self.active:
                self.draw_cooldown(surf, topleft, self.active.current_charge, self.active.required_charge)
            elif self.automatic:
                self.draw_cooldown(surf, topleft, self.automatic.current_charge, self.automatic.required_charge)
            elif self.count:
                self.draw_cooldown(surf, topleft, self.count.count, self.count.orig_count)

    def draw_cooldown(self, surf, topleft, current, total):
        if total <= 0:
            return
        index = int(current*8//total)
        if index >= 8:
            pass
        else:
            chosen_cooldown = Engine.subsurface(self.cooldown, (16*index, 0, 16, 16))
            surf.blit(chosen_cooldown, topleft) 

    def get_help_box(self):
        if not self.help_box:
            self.help_box = InfoMenu.Help_Dialog(self.desc)
        return self.help_box

    # If the attribute is not found
    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            return super(Status, self).__getattr__(attr)
        return None

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__.update(d)

class TimeComponent(object):
    def __init__(self, time_left):
        self.time_left = int(time_left)
        self.total_time = self.time_left

    def decrement(self):
        self.time_left -= 1

    def increment(self):
        self.time_left += 1
        self.time_left = min(self.time_left, self.total_time)

class UpkeepStatChangeComponent(object):
    def __init__(self, change_in_stats):
        self.stat_change = change_in_stats
        self.count = 0

class HPPercentageComponent(object):
    def __init__(self, percentage):
        self.percentage = int(percentage)

class ConditionalComponent(object):
    def __init__(self, name, value, conditional):
        self.name = name
        self.value = value
        self.conditional = conditional

    def __repr__(self):
        return self.value

class StatHalveComponent(object):
    def __init__(self, line):
        self.stats = line.split(',')
        self.penalties = [None for _ in self.stats]

class CountComponent(object):
    def __init__(self, orig_count):
        self.orig_count = int(orig_count)
        self.count = int(orig_count)

class UpkeepAnimationComponent(object):
    def __init__(self, animation_name, x, y, num_frames):
        self.animation_name = animation_name
        self.x = int(x)
        self.y = int(y)
        self.num_frames = int(num_frames)

    def removeSprites(self):
        self.sprite = None

    def loadSprites(self):
        self.sprite = GC.IMAGESDICT[self.animation_name]

class AlwaysAnimationComponent(object):
    def __init__(self, animation_name, x, y, num_frames):
        self.animation_name = animation_name
        self.x = int(x)
        self.y = int(y)
        self.num_frames = int(num_frames)
        self.frameCount = 0
        self.lastUpdate = Engine.get_time()
        self.animation_speed = 150

    def removeSprites(self):
        self.image = None
        self.sprite = None

    def loadSprites(self):
        self.sprite = GC.IMAGESDICT[self.animation_name]
        self.image = Engine.subsurface(self.sprite, (0, 0, self.sprite.get_width()//self.x, self.sprite.get_height()//self.y))

class UnitTintComponent(object):
    def __init__(self, data):
        color1, color2, color3, period, width, max_alpha = data.split(',')
        self.color = (int(color1), int(color2), int(color3))
        self.period = int(period)
        self.width = int(width)
        self.max_alpha = float(max_alpha)

# === STATUS PROCESSOR =========================================================
class Status_Processor(object):
    def __init__(self, gameStateObj, upkeep=True):
        # Initial setup
        self.upkeep = upkeep # Whether I'm running this on upkeep or on endstep
        self.current_phase = gameStateObj.phase.get_current_phase()
        self.previous_phase = gameStateObj.phase.get_previous_phase()
        affected_units = [unit for unit in gameStateObj.allunits if unit.position and unit.status_effects]
        if self.upkeep:
            self.units = [unit for unit in affected_units if unit.team == self.current_phase]
        else:
            self.units = [unit for unit in affected_units if unit.team == self.previous_phase]
        logger.info('Building Status_Processor: %s %s %s', self.upkeep, self.current_phase, self.previous_phase)

        # State control
        self.current_unit = None
        self.current_unit_statuses = []
        self.current_status = None
        self.status_index = 0
        self.state = CustomObjects.StateMachine('begin')
        self.state_buffer = False

        # Animation properties
        self.time_spent_on_each_status = 1200 # Only if it has a onetime animation
        self.start_time_for_this_status = Engine.get_time()

        # Health bar
        self.health_bar = Interaction.HealthBar('splash', None, None)

        # Waiting timer
        self.wait_time = 200
        self.started_waiting = Engine.get_time()

    def update(self, gameStateObj):
        current_time = Engine.get_time()

        # Beginning process
        if self.state.getState() == 'begin':
            if self.units:
                self.current_unit = self.units.pop()
                self.state.changeState('new_unit')
            else:
                return "Done" # Done

        # New unit
        elif self.state.getState() == 'new_unit':
            # Get all statuses that could affect this unit
            self.current_unit_statuses = self.current_unit.status_effects
            self.status_index = 0

            # Get status
            if self.current_unit_statuses:
                self.health_bar.change_unit(self.current_unit, None)
                self.state.changeState('new_status')
            else: # This unit has no status to process. Return and get a new one
                self.state.changeState('begin')

        elif self.state.getState() == 'new_status':
            if self.status_index < len(self.current_unit_statuses):
                self.current_status = self.current_unit_statuses[self.status_index]
                self.status_index += 1
                # Returns true if status is going to be processed...
                # Handle status
                if self.upkeep:
                    output = HandleStatusUpkeep(self.current_status, self.current_unit, gameStateObj)
                else:
                    output = HandleStatusEndStep(self.current_status, self.current_unit, gameStateObj)

                if output == "Remove": # Returns "Remove" if status has run out of time and should just be removed
                    Action.do(Action.RemoveStatus(self.current_unit, self.current_status), gameStateObj)
                    self.state.changeState('new_status')
                else:
                    self.oldhp = output[0]
                    self.newhp = output[1]
                    # If the hp_changed or the current status has a one time animation, run the process, otherwise, move onto next status
                    # Processing state handles animation and HP updating
                    if self.oldhp != self.newhp:
                        logger.debug('HP change: %s %s', self.oldhp, self.newhp)
                        # self.health_bar.update()
                        # self.start_time_for_this_status = current_time + self.health_bar.time_for_change - 400
                        gameStateObj.cursor.setPosition(self.current_unit.position, gameStateObj)
                        self.current_unit.sprite.change_state('status_active', gameStateObj)
                        self.state.changeState('processing')
                        gameStateObj.stateMachine.changeState('move_camera')
                        return "Waiting"
                    else:
                        self.state.changeState('new_status')
            else: # This unit has no more status to process. Return and get a new unit
                self.state.changeState('begin')

        elif self.state.getState() == 'processing':
            self.health_bar.update(status_obj=True)
            # Turn on animations
            for anim in gameStateObj.allanimations:
                anim.on = True
            # Done waiting for status, process next one
            if current_time - self.start_time_for_this_status - self.health_bar.time_for_change + 400 > self.time_spent_on_each_status:
                # handle death of a unit
                if self.current_unit.currenthp <= 0:
                    self.current_unit.isDying = True
                    gameStateObj.stateMachine.changeState('dying')
                    self.state.changeState('begin')
                    return "Death"
                else:
                    self.state.changeState('new_status')
                self.current_unit.sprite.change_state('normal', gameStateObj)
            else:
                return "Waiting"

        elif self.state.getState() == 'wait':
            # Done waiting, head back
            if current_time - self.wait_time > self.started_waiting:
                self.state.back()
            else:
                return "Waiting"

    def check_active(self, unit):
        if unit is self.current_unit and self.state.getState() == 'processing':
            return True
        return False

    def draw(self, surf, gameStateObj):
        # This is so it doesn't draw the first time it goes to processing, which is before the camera moves
        if self.state_buffer:
            self.health_bar.draw(surf, gameStateObj)
        if self.state.getState() == 'processing':
            self.state_buffer = True
        else:
            self.state_buffer = False

def check_automatic(status, unit, gameStateObj):
    if status.automatic and status.automatic.check_charged():
        Action.do(Action.FinalizeAutomaticSkill(status, unit), gameStateObj)
        
def HandleStatusUpkeep(status, unit, gameStateObj):
    oldhp = unit.currenthp
    if status.time:
        Action.do(Action.DecrementStatusTime(status), gameStateObj)
        logger.info('Time Status %s to %s at %s. Time left: %s', status.id, unit.name, unit.position, status.time.time_left)
        if status.time.time_left <= 0:
            return "Remove" # Don't process. Status has no more effect on unit

    elif status.remove_range:
        p_unit = gameStateObj.get_unit_from_id(status.owner_id)
        if not p_unit or not p_unit.position or not unit.position or Utility.calculate_distance(p_unit.position, unit.position) > status.remove_range:
            return "Remove"

    if status.hp_percentage:
        hp_change = int(int(unit.stats['HP']) * status.hp_percentage.percentage/100.0)
        old_hp = unit.currenthp
        Action.do(Action.ChangeHP(unit, hp_change), gameStateObj)
        if unit.currenthp > old_hp:
            GC.SOUNDDICT['MapHeal'].play()

    elif status.upkeep_damage:
        if ',' in status.upkeep_damage:
            low_damage, high_damage = status.upkeep_damage.split(',')
            damage_dealt = static_random.shuffle(range(int(low_damage), int(high_damage)))[0]
        else:
            damage_dealt = int(status.upkeep_damage)
        old_hp = unit.currenthp
        Action.do(Action.ChangeHP(unit, damage_dealt), gameStateObj)
        if unit.currenthp > old_hp:
            GC.SOUNDDICT['MapHeal'].play()

    if status.upkeep_stat_change:
        Action.do(Action.ApplyStatChange(unit, status.upkeep_stat_change.stat_change), gameStateObj)
        Action.do(Action.ChangeStatusCount(status.upkeep_stat_change, status.upkeep_stat_change.count + 1), gameStateObj)

    check_automatic(status, unit, gameStateObj)

    if status.upkeep_animation and unit.currenthp != oldhp:
        stota = status.upkeep_animation
        if not stota.sprite:
            logger.error('Missing upkeep animation sprite for %s', status.name)
        else:
            anim = CustomObjects.Animation(stota.sprite, (unit.position[0], unit.position[1] - 1), (stota.x, stota.y), stota.num_frames, on=False)
            gameStateObj.allanimations.append(anim)

    if status.upkeeps_movement:
        if unit.team.startswith('enemy'):
            gameStateObj.boundary_manager._remove_unit(unit, gameStateObj)
            if unit.position:
                gameStateObj.boundary_manager._add_unit(unit, gameStateObj)

    # unit.change_hp(0)  # Just check bounds
    # # if unit.currenthp > int(unit.stats['HP']):
    # #     unit.currenthp = int(unit.stats['HP'])
    # if unit.movement_left > int(unit.stats['MOV']):
    #     unit.movement_left = max(0, int(unit.stats['MOV']))

    return oldhp, unit.currenthp 

def HandleStatusEndStep(status, unit, gameStateObj):
    oldhp = unit.currenthp

    if status.endstep_stat_change:
        Action.do(Action.ApplyStatChange(unit, status.endstep_stat_change.stat_change), gameStateObj)
        Action.do(Action.ChangeStatusCount(status.endstep_stat_change, status.endstep_stat_change.count + 1), gameStateObj)

    if status.lost_on_endstep:
        Action.do(Action.RemoveStatus(unit, status), gameStateObj)

    return oldhp, unit.currenthp

# === STATUS PARSER ======================================================
# Takes one status id, as well as the database of status data, and outputs a status object.
def statusparser(s_id, gameStateObj=None):
    def find(text):
    for status in GC.STATUSDATA.getroot().findall('status'):
        if status.find('id').text == s_id:
            components = status.find('components').text
            if components:
                components = components.split(',')
            else:
                components = []
            name = status.get('name')
            desc = status.find('desc').text
            image_index = status.find('image_index').text if status.find('image_index') is not None else None
            if image_index:
                image_index = tuple(int(num) for num in image_index.split(','))
            else:
                image_index = (0, 0)

            my_components = {}
            for component in components:
                if component == 'time':
                    time = status.find('time').text
                    my_components['time'] = TimeComponent(time)
                elif component == 'stat_change':
                    my_components['stat_change'] = Utility.intify_comma_list(status.find('stat_change').text)
                    my_components['stat_change'].extend([0] * (cf.CONSTANTS['num_stats'] - len(my_components['stat_change'])))
                elif component == 'growth_mod':
                    my_components['growth_mod'] = Utility.intify_comma_list(status.find('growth_mod').text)
                    my_components['growth_mod'].extend([0] * (cf.CONSTANTS['num_stats'] - len(my_components['growth_mod'])))
                elif component == 'upkeep_stat_change':
                    stat_change = Utility.intify_comma_list(status.find('upkeep_stat_change').text)
                    stat_change.extend([0] * (cf.CONSTANTS['num_stats'] - len(stat_change)))
                    my_components['upkeep_stat_change'] = UpkeepStatChangeComponent(stat_change)
                elif component == 'endstep_stat_change':
                    stat_change = Utility.intify_comma_list(status.find('endstep_stat_change').text)
                    stat_change.extend([0] * (cf.CONSTANTS['num_stats'] - len(stat_change)))
                    my_components['endstep_stat_change'] = UpkeepStatChangeComponent(stat_change)
                # Combat changes
                elif component.startswith('conditional_'):
                    value, conditional = status.find(component).text.split(';')
                    my_components[component] = ConditionalComponent(component, value, conditional)
                # Others...
                elif component == 'stat_halve':
                    my_components['stat_halve'] = StatHalveComponent(status.find('stat_halve').text)
                elif component == 'count':
                    my_components['count'] = CountComponent(int(status.find('count').text))
                elif component == 'caretaker':
                    my_components['caretaker'] = int(status.find('caretaker').text)
                elif component == 'remove_range':
                    my_components['remove_range'] = int(status.find('remove_range').text)
                elif component == 'buy_value_mod':
                    my_components['buy_value_mod'] = float(status.find('buy_value_mod').text)
                elif component == 'hp_percentage':
                    percentage = status.find('hp_percentage').text
                    my_components['hp_percentage'] = HPPercentageComponent(percentage)
                elif component == 'upkeep_animation':
                    info_line = status.find('upkeep_animation').text
                    split_line = info_line.split(',')
                    my_components['upkeep_animation'] = UpkeepAnimationComponent(split_line[0], split_line[1], split_line[2], split_line[3])
                elif component == 'always_animation':
                    info_line = status.find('always_animation').text
                    split_line = info_line.split(',')
                    my_components['always_animation'] = AlwaysAnimationComponent(split_line[0], split_line[1], split_line[2], split_line[3])
                elif component == 'unit_tint':
                    info_line = status.find('unit_tint').text
                    my_components['unit_tint'] = UnitTintComponent(info_line)
                elif component == 'item_mod':
                    conditional = status.find('item_mod_conditional').text if status.find('item_mod_conditional') is not None else None
                    effect_add = status.find('item_mod_effect_add').text.split(';') if status.find('item_mod_effect_add') is not None else None
                    effect_change = status.find('item_mod_effect_change').text.split(';') if status.find('item_mod_effect_change') is not None else None
                    my_components['item_mod'] = ActiveSkill.ItemModComponent(s_id, conditional, effect_add, effect_change)
                elif component == 'aura':
                    aura_range = int(status.find('range').text)
                    child = status.find('child').text
                    target = status.find('target').text
                    my_components['aura'] = Aura.Aura(aura_range, target, child, gameStateObj)
                elif component == 'combat_art' or component == 'automatic_combat_art':
                    mode = ActiveSkill.Mode.ACTIVATED if component == 'combat_art' else ActiveSkill.Mode.AUTOMATIC
                    child_status = status.find('combat_art_status').text if status.find('combat_art_status') is not None else None
                    charge_method = status.find('charge_method').text if status.find('charge_method') is not None else 'SKL'
                    charge_max = int(status.find('charge_max').text) if status.find('charge_max') is not None else 60
                    valid_weapons_func = exec(status.find('valid_weapons_func').text) if status.find('valid_weapons_func') is not None else lambda (self, u, w): w
                    check_valid_func = exec(status.find('check_valid_func').text) if status.find('check_valid_func') is not None else lambda (self, u, gameStateObj): True
                    my_components[component] = ActiveSkill.CombatArtComponent(mode, child_status, valid_weapons_func, check_valid_func, charge_method, charge_max)
                elif component == 'activated_item':
                    activated_item_id = status.find('activated_item').text if status.find('activated_item') is not None else None
                    charge_method = status.find('charge_method').text if status.find('charge_method') is not None else 'SKL'
                    charge_max = int(status.find('charge_max').text) if status.find('charge_max') is not None else 0
                    check_valid_func = exec(status.find('check_valid_func').text) if status.find('check_valid_func') is not None else lambda (self, u, gameStateObj): True
                    get_choices_func = exec(status.find('get_choices_func').text) if status.find('get_choices_func') is not None else lambda (self, u, gameStateObj): None
                    my_components['activated_item'] = ActiveSkill.ActivatedItemComponent(activated_item_id, check_valid_func, get_choices_func, charge_method, charge_max)
                elif component == 'proc':
                    child_status = status.find('proc_status').text if status.find('proc_status') is not None else None
                    charge_method = status.find('proc_rate').text if status.find('proc_rate') is not None else 'SKL'
                    priority = int(status.find('proc_priority').text) if status.find('proc_priority') is not None else 10
                    valid_items_func = exec(status.find('valid_items_func').text) if status.find('valid_items_func') is not None else lambda (self, w): w
                    my_components['proc'] = ActiveSkill.ProcComponent(child_status, charge_method, priority)
                elif status.find(component) is not None and status.find(component).text:
                    my_components[component] = status.find(component).text
                else:
                    my_components[component] = True

            currentStatus = Status(s_id, name, my_components, desc, image_index)
            if gameStateObj:
                gameStateObj.register_status(currentStatus)
            # Otherwise already registered

            return currentStatus

def deserialize(s_dict):
    status = statusparser(s_dict['id'])
    if not status:
        return
    status.uid = s_dict['uid']

    if s_dict['time_left'] is not None:
        status.time.time_left = s_dict['time_left']
    # if s_dict['count'] is not None:
    #     status.count.count = s_dict['count']
    if s_dict['upkeep_sc_count'] is not None:
        status.upkeep_stat_change.count = s_dict['upkeep_sc_count']
    # if s_dict['active_charge'] is not None:
    #     status.active.current_charge = s_dict['active_charge']
    # if s_dict.get('automatic_charge') is not None:
    #     status.automatic.current_charge = s_dict['automatic_charge']
    if s_dict['stat_halve_penalties'] is not None:
        status.stat_halve.penalties = s_dict['stat_halve_penalties']
    if s_dict['aura_child_uid'] is not None:
        status.aura.child_uid = s_dict['aura_child_uid']
    status.children = set(s_dict['children'])
    status.owner_id = s_dict['owner_id']
    status.giver_id = s_dict['giver_id']
    status.data = s_dict.get('data', {})  # Get back persistent data
    if s_dict.get('activated_item') is not None:
        status.activated_item.current_charge = s_dict['activated_item']
    if s_dict.get('combat_art') is not None:
        status.combat_art.current_charge = s_dict['combat_art']

    return status

def attach_to_unit(status, unit):
    """
    Done (on load) after loading both the unit and the status to attach 
    the status correctly to the unit after a suspend.
    """
    if status.item_mod:
        for item in unit.items:
            status.item_mod.apply_mod(item)
    unit.status_effects.append(status)
    unit.status_bundle.update(list(status.components))

# Populate feat_list
def get_feat_list(status_data):
    for status in status_data.getroot().findall('status'):
        if status.find('id').text == 'Feat':
            feat_list = status.find('feat_list').text if status.find('feat_list') is not None else ''
            return feat_list.split(',')
    return []

feat_list = get_feat_list(GC.STATUSDATA)
