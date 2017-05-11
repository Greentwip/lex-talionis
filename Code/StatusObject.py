# === Imports ==================================================================
# Custom imports
from imagesDict import getImages
from GlobalConstants import *
import CustomObjects, TileObject, ActiveSkill, Interaction, SaveLoad, InfoMenu, UnitObject, Utility, Engine
import copy

import logging
logger = logging.getLogger(__name__)

# === New Status Object ========================================================
class StatusObject(object):
    def __init__(self, s_id, name, components, desc, icon_index=(0,0)):
        self.id = s_id
        self.name = name
        self.desc = desc
        self.icon_index = icon_index

        self.children = []

        # Creates component slots
        self.components = components # Consumable, Weapon, Spell Bigger Picture
        for component_key, component_value in self.components.iteritems():
            self.__dict__[component_key] = component_value

        self.loadSprites()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def removeSprites(self):
        self.icon = None
        self.cooldown = None
        if self.upkeep_animation:
            self.upkeep_animation.removeSprites()
        if self.always_animation:
            self.always_animation.removeSprites()
        if self.active and self.active.item:
            self.active.item.removeSprites()

    def loadSprites(self):
        self.icon = Engine.subsurface(ITEMDICT['Skills'], (16*self.icon_index[0], 16*self.icon_index[1], 16, 16)) if self.icon_index else None
        self.cooldown = IMAGESDICT['IconCooldown']
        if self.upkeep_animation:
            self.upkeep_animation.loadSprites()
        if self.always_animation:
            self.always_animation.loadSprites()
        if self.active and self.active.item:
            self.active.item.loadSprites()

    def serialize(self):
        serial_dict = {}
        serial_dict['id'] = self.id
        serial_dict['time_left'] = self.time.time_left if self.time else None
        serial_dict['upkeep_sc_count'] = self.upkeep_stat_change.count if self.upkeep_stat_change else None
        serial_dict['rhythm_sc_count'] = self.rhythm_stat_change.count if self.rhythm_stat_change else None
        serial_dict['charge'] = self.active.current_charge if self.active else None
        serial_dict['children'] = self.children
        serial_dict['parent_id'] = self.parent_id
        serial_dict['count'] = self.count.count if self.count else None
        if self.rescue:
            serial_dict['rescue'] = (self.rescue.skl_penalty, self.rescue.spd_penalty)
        return serial_dict

    def draw(self, surf, topleft, cooldown=True):
        if self.icon:
            surf.blit(self.icon, topleft)

        # Cooldown
        if cooldown:
            if self.active:
                self.draw_cooldown(surf, topleft, self.active.current_charge, self.active.required_charge)
            elif self.count:
                self.draw_cooldown(surf, topleft, self.count.count, self.count.orig_count)

    def draw_cooldown(self, surf, topleft, current, total):
        if total <= 0:
            return
        index = int(current*8/total)
        if index >= 8:
            pass
        else:
            chosen_cooldown = Engine.subsurface(self.cooldown, (16*index,0,16,16))
            surf.blit(chosen_cooldown, topleft) 

    def get_help_box(self):
        return InfoMenu.create_help_box(self.desc)

    def remove_children(self, gameStateObj):
        logger.debug('Removing children from %s', self.id)
        for u_id in reversed(self.children):
            child_unit = gameStateObj.get_unit_from_id(u_id)
            if child_unit:
                for c_status in child_unit.status_effects:
                    if c_status.id == self.tether:
                        HandleStatusRemoval(c_status, child_unit, gameStateObj)
                        break
        self.children = []

    # If the attribute is not found
    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            return super(StatusObject, self).__getattr__(attr)
        return None

    def __getstate__(self): return self.__dict__
    def __setstate__(self, d): self.__dict__.update(d)

class TimeComponent(object):
    def __init__(self, time_left):
        self.name = 'time'
        self.time_left = int(time_left)
        self.total_time = self.time_left

    def decrement(self):
        self.time_left -= 1

class UpkeepStatChangeComponent(object):
    def __init__(self, change_in_stats):
        self.name = "UpkeepStatChange"
        self.stat_change = change_in_stats
        self.count = 0

class RhythmStatChangeComponent(object):
    def __init__(self, change, reset, init_count, limit):
        self.name = "RhythmStatChange"
        self.change = change
        self.count = init_count
        self.limit = limit
        self.reset = reset

class HPPercentageComponent(object):
    def __init__(self, percentage):
        self.name = "hppercentage"
        self.percentage = int(percentage)

class ConditionalComponent(object):
    def __init__(self, name, value, conditional):
        self.name = name
        self.value = value
        self.conditional = conditional

    def __repr__(self):
        return self.value

class WeaknessComponent(object):
    def __init__(self, damage_type, num):
        self.name = "weakness"
        self.damage_type = damage_type
        self.num = num

class RescueComponent(object):
    def __init__(self):
        self.skl_penalty = None
        self.spd_penalty = None

class CountComponent(object):
    def __init__(self, orig_count):
        self.orig_count = int(orig_count)
        self.count = int(orig_count)

class UpkeepAnimationComponent(object):
    def __init__(self, animation_name, x, y, num_frames):
        self.name = "upkeep_animation"
        self.animation_name = animation_name
        self.x = int(x)
        self.y = int(y)
        self.num_frames = int(num_frames)

    def removeSprites(self):
        self.sprite = None

    def loadSprites(self):
        self.sprite = IMAGESDICT[self.animation_name]

class AlwaysAnimationComponent(object):
    def __init__(self, animation_name, x, y, num_frames):
        self.name = "alwaysanimation"
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
        self.sprite = IMAGESDICT[self.animation_name]
        self.image = Engine.subsurface(self.sprite, (0,0,self.sprite.get_width()/self.x, self.sprite.get_height()/self.y))

# === STATUS PROCESSOR =========================================================
class Status_Processor(object):
    def __init__(self, gameStateObj, upkeep=True):
        # Initial setup
        self.upkeep = upkeep # Whether I'm running this on upkeep or on endstep
        self.current_phase = gameStateObj.statedict['phases'][gameStateObj.statedict['current_phase']].name
        self.previous_phase = gameStateObj.statedict['phases'][gameStateObj.statedict['previous_phase']].name
        affected_units = [unit for unit in gameStateObj.allunits if unit.position and (unit.status_effects or 'Status' in gameStateObj.map.tile_info_dict[unit.position])]
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
        self.health_bar = Interaction.HealthBar('auto', None, None, time_for_change=self.time_spent_on_each_status)

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
                #gameStateObj.cursor.setPosition(self.current_unit.position, gameStateObj)
                #self.current_unit.isActive = True
                self.state.changeState('new_status')
                if any(status.upkeep_animation for status in self.current_unit_statuses):
                    self.state.changeState('wait')
                    self.started_waiting = current_time
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
                    HandleStatusRemoval(self.current_status, self.current_unit, gameStateObj)
                    self.state.changeState('new_status')
                else:
                    self.oldhp = output[0]
                    self.newhp = output[1]
                    # If the hp_changed or the current status has a one time animation, run the process, otherwise, move onto next status
                    # Processing state handles animation and HP updating
                    if self.current_status.upkeep_animation or self.oldhp != self.newhp:
                        logger.debug('HP change: %s %s', self.oldhp, self.newhp)
                        self.start_time_for_this_status = current_time
                        gameStateObj.cursor.setPosition(self.current_unit.position, gameStateObj)
                        self.state.changeState('processing')
                        gameStateObj.stateMachine.changeState('move_camera')
                        return "Waiting"
                    else:
                        self.state.changeState('new_status')
            else: # This unit has no more status to process. Return and get a new unit
                #self.current_unit.isActive = False
                self.state.changeState('begin')

        elif self.state.getState() == 'processing':
            self.health_bar.update()
            # Done waiting for status, process next one
            if current_time - self.start_time_for_this_status > self.time_spent_on_each_status:
                # handle death of a unit
                if self.current_unit.currenthp <= 0:
                    self.current_unit.isDying = True
                    gameStateObj.stateMachine.changeState('dying')
                    self.state.changeState('begin')
                    return "Death"
                else:
                    self.state.changeState('new_status')
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
        
def HandleStatusUpkeep(status, unit, gameStateObj):
    oldhp = unit.currenthp
    if status.time:
        status.time.decrement()
        logger.info('Time Status %s to %s at %s. Time left: %s', status.id, unit.name, unit.position, status.time.time_left)
        if status.time.time_left <= 0:
            return "Remove" # Don't process. Status has no more effect on unit

    elif status.remove_range:
        p_unit = gameStateObj.get_unit_from_id(status.parent_id)
        if not p_unit or not p_unit.position or not unit.position or Utility.calculate_distance(p_unit.position, unit.position) > status.remove_range:
            return "Remove"

    if status.hp_percentage:
        hp_change = int(int(unit.stats['HP']) * status.hp_percentage.percentage/100.0)
        unit.currenthp += hp_change

    if status.upkeep_stat_change:
        unit.apply_stat_change(status.upkeep_stat_change.stat_change)
        status.upkeep_stat_change.count += 1

    if status.rhythm_stat_change:
        status.rhythm_stat_change.count += 1
        if status.rhythm_stat_change.count > status.rhythm_stat_change.limit:
            status.rhythm_stat_change.count = 0
            unit.apply_stat_change(status.rhythm_stat_change.reset)
        else:
            unit.apply_stat_change(status.rhythm_stat_change.change)

    if status.upkeep_animation:
        stota = status.upkeep_animation
        if not stota.sprite:
            logger.error('Missing upkeep animation sprite for %s', status.name)
        else:
            gameStateObj.allanimations.append(CustomObjects.Animation(stota.sprite, (unit.position[0], unit.position[1] - 1), (stota.x, stota.y), stota.num_frames))

    if status.upkeeps_movement:
        if unit.team.startswith('enemy'):
            gameStateObj.boundary_manager._remove_unit(unit, gameStateObj)
            if unit.position:
                gameStateObj.boundary_manager._add_unit(unit, gameStateObj)

    if unit.currenthp > int(unit.stats['HP']):
        unit.currenthp = int(unit.stats['HP'])
    if unit.movement_left > int(unit.stats['MOV']):
        unit.movement_left = max(0, int(unit.stats['MOV']))

    return oldhp, unit.currenthp 

def HandleStatusEndStep(status, unit, gameStateObj):
    oldhp = unit.currenthp
    """
    # Increases skill charge on endstep
    if status.active and status.active.current_charge < status.active.required_charge:
        status.active.current_charge += unit.stats['SKL']
        if status.active.current_charge >= status.active.required_charge:
            status.active.current_charge = status.active.required_charge
            # TODO Display Animation
    """
    if status.endstep_stat_change:
        unit.apply_stat_change(status.endstep_stat_change.stat_change)
        status.endstep_stat_change.count += 1

    if status.endstep_rhythm_stat_change:
        status.endstep_rhythm_stat_change.count += 1
        if status.endstep_rhythm_stat_change.count > status.endstep_rhythm_stat_change.limit:
            status.endstep_rhythm_stat_change.count = 0
            unit.apply_stat_change(status.endstep_rhythm_stat_change.reset)
        else:
            unit.apply_stat_change(status.endstep_rhythm_stat_change.change)

    return oldhp, unit.currenthp

def HandleStatusAddition(status, unit, gameStateObj=None):
    logger.info('Adding Status %s to %s at %s', status.id, unit.name, unit.position)
    if not isinstance(unit, UnitObject.UnitObject):
        return
    # Check to see if we need to remove other statuses
    for other_status in unit.status_effects:
        # If this is a status that doesn't say it stacks, remove older versions of it
        if other_status.id == status.id and not status.stack:
            logger.info('Status %s already present', status.id)
            if status.time or status.remove_range:
                HandleStatusRemoval(other_status, unit, gameStateObj)
            if status.aura_child:
                return # Just ignore this new one

    # Check to see if we should reflect this status back at user
    if not status.already_reflected and any(other_status.reflect for other_status in unit.status_effects) and status.parent_id and not status.aura_child:
        p_unit = gameStateObj.get_unit_from_id(status.parent_id)
        s_copy = copy.deepcopy(status) # Create a copy of this status
        s_copy.parent_id = unit.id
        s_copy.already_reflected = True # So we don't get infinite reflections
        HandleStatusAddition(s_copy, p_unit, gameStateObj)
            
    unit.status_effects.append(status)

    if status.convert:
        status.original_team = unit.team
        p_unit = gameStateObj.get_unit_from_id(status.parent_id)
        unit.changeTeams(p_unit.team, gameStateObj)

    if status.stat_change:
        unit.apply_stat_change(status.stat_change)

    if status.rescue:
        # Rescue penalty
        status.rescue.skl_penalty = -unit.stats['SKL'].base_stat/2
        unit.stats['SKL'].bonuses += status.rescue.skl_penalty
        status.rescue.spd_penalty = -unit.stats['SPD'].base_stat/2
        unit.stats['SPD'].bonuses += status.rescue.spd_penalty

    if status.refresh:
        unit.reset()

    if status.skill_restore:
        activated_skills = [status for status in unit.status_effects if status.active]
        for activated_skill in activated_skills:
            activated_skill.active.current_charge = activated_skill.active.required_charge

    if status.name == "Clumsy":
        if any(status.horsemanship for status in unit.status_effects):
            HandleStatusRemoval(status, unit, gameStateObj)
    if status.horsemanship:
        for status in unit.status_effects:
            if status.name == "Clumsy":
                HandleStatusRemoval(status, unit, gameStateObj)

    if status.flying:
        unit.remove_tile_status(gameStateObj, force=True)

    if status.passive:
        for item in unit.items:
            status.passive.apply_mod(item)

    if status.clear:
        for status in unit.status_effects:
            if status.time:
                HandleStatusRemoval(status, unit, gameStateObj)

    if status.momentary:
        HandleStatusRemoval(status, unit, gameStateObj)

    # when you gain shrugg off, lower negative status ailments to 0
    if status.shrug_off:
        for status in unit.status_effects:
            if status.time and status.negative and status.time.time_left > 2:
                status.time.time_left = 2

    # If you have shrug off, lower this ailment, if temporary, to 0
    if any(status.shrug_off for status in unit.status_effects):
        if status.time and status.time > 2:
            status.time.time_left = 2

    if status.affects_movement and gameStateObj.boundary_manager:
        if unit.team.startswith('enemy'):
            gameStateObj.boundary_manager._remove_unit(unit, gameStateObj)
            if unit.position:
                gameStateObj.boundary_manager._add_unit(unit, gameStateObj)

    # Status Always Animations are handle by the unit themselves, in their draw function they look at the 
    # current status effects affecting them and check if any have always animations. If they do, they draw them...
    return status

def HandleStatusRemoval(status, unit, gameStateObj=None):
    if not isinstance(status, StatusObject):
        # Must be a unique id
        for s in unit.status_effects:
            if status == s.id:
                status = s
                break 
        else:
            logger.warning('Status ID %s not present...', status)
            logger.warning(unit.status_effects)
            return
            
    logger.info('Removing status %s from %s at %s', status.id, unit.name, unit.position)
    if status in unit.status_effects:
        unit.status_effects.remove(status)
    else:
        logger.warning('Status %s %s not present...', status.id, status.name)
        logger.warning(unit.status_effects)
        return
    if status.convert:
        unit.changeTeams(status.original_team, gameStateObj)
    if status.upkeep_stat_change:
        unit.apply_stat_change([-stat*(status.upkeep_stat_change.count) for stat in status.upkeep_stat_change.stat_change])
    if status.stat_change:
        unit.apply_stat_change([-stat for stat in status.stat_change])
    if status.rescue:
        unit.stats['SKL'].bonuses -= status.rescue.skl_penalty
        unit.stats['SPD'].bonuses -= status.rescue.spd_penalty
    if status.flying:
        unit.acquire_tile_status(gameStateObj, force=True)
    if status.passive:
        for item in unit.items:
            status.passive.remove_mod(item)
    # Tell the parent status that it is not connected to me anymore
    if status.aura_child:
        status.parent_status.remove_child(unit)
    if status.tether:
        status.remove_children()
    if status.status_on_complete:
        HandleStatusAddition(statusparser(status.status_on_complete), unit, gameStateObj)
    if status.ephemeral:
        unit.isDying = True
        unit.currenthp = 0
        gameStateObj.stateMachine.changeState('dying')
    if status.affects_movement and gameStateObj.boundary_manager:
        if unit.team.startswith('enemy'):
            gameStateObj.boundary_manager._remove_unit(unit, gameStateObj)
            if unit.position:
                gameStateObj.boundary_manager._add_unit(unit, gameStateObj)

# === STATUS PARSER ======================================================
# Takes one status id, as well as the database of status data, and outputs a status object.
def statusparser(s_id):
    Status = []
    if s_id: # itemstring needs to exist
        for status in STATUSDATA.getroot().findall('status'):
            if status.find('id').text == s_id:
                components = status.find('components').text
                if components:
                    components = components.split(',')
                else:
                    components = []
                name = status.get('name')
                desc = status.find('desc').text
                icon_index = status.find('icon_index').text if status.find('icon_index') is not None else None
                if icon_index:
                    icon_index = tuple(int(num) for num in icon_index.split(','))
                else:
                    icon_index = (0,0)

                my_components = {}
                for component in components:
                    if component == 'time':
                        time = status.find('time').text
                        my_components['time'] = TimeComponent(time)
                    elif component == 'stat_change':
                        my_components['stat_change'] = SaveLoad.intify_comma_list(status.find('stat_change').text)
                    elif component == 'upkeep_stat_change':
                        stat_change = SaveLoad.intify_comma_list(status.find('upkeep_stat_change').text)
                        my_components['upkeep_stat_change'] = UpkeepStatChangeComponent(stat_change)
                    elif component == 'endstep_stat_change':
                        stat_change = SaveLoad.intify_comma_list(status.find('endstep_stat_change').text)
                        my_components['endstep_stat_change'] = UpkeepStatChangeComponent(stat_change)
                    elif component == 'rhythm_stat_change':
                        change, reset, init_count, limit = status.find('rhythm_stat_change').text.split(';')
                        change = SaveLoad.intify_comma_list(change)
                        reset = SaveLoad.intify_comma_list(reset)
                        init_count = int(init_count)
                        limit = int(limit)
                        my_components['rhythm_stat_change'] = RhythmStatChangeComponent(change, reset, init_count, limit)
                    elif component == 'endstep_rhythm_stat_change':
                        change, reset, init_count, limit = status.find('endstep_rhythm_stat_change').text.split(';')
                        change = SaveLoad.intify_comma_list(change)
                        reset = SaveLoad.intify_comma_list(reset)
                        init_count = int(init_count)
                        limit = int(limit)
                        my_components['endstep_rhythm_stat_change'] = RhythmStatChangeComponent(change, reset, init_count, limit)
                    # Combat changes
                    elif component == 'avoid':
                        avoid = status.find('avoid').text
                        my_components['avoid'] = avoid
                    elif component == 'hit':
                        hit = status.find('hit').text
                        my_components['hit'] = hit
                    elif component == 'mt':
                        mt = status.find('mt').text
                        my_components['mt'] = mt
                    elif component == 'conditional_avoid':
                        avoid, conditional = status.find('conditional_avoid').text.split(';')
                        my_components['conditional_avoid'] = ConditionalComponent('conditional_avoid', avoid, conditional)
                    elif component == 'conditional_hit':
                        hit, conditional = status.find('conditional_hit').text.split(';')
                        my_components['conditional_hit'] = ConditionalComponent('conditional_hit', hit, conditional)
                    elif component == 'conditional_mt':
                        mt, conditional = status.find('conditional_mt').text.split(';')
                        my_components['conditional_mt'] = ConditionalComponent('conditional_mt', mt, conditional)
                    elif component == 'conditional_resist':
                        mt, conditional = status.find('conditional_resist').text.split(';')
                        my_components['conditional_resist'] = ConditionalComponent('conditional_resist', mt, conditional)
                    elif component == 'dynamic_avoid':
                        avoid, dynamic = status.find('dynamic_avoid').text.split(';')
                        my_components['dynamic_avoid'] = ConditionalComponent('dynamic_avoid', avoid, dynamic)
                    elif component == 'dynamic_hit':
                        hit, dynamic = status.find('dynamic_hit').text.split(';')
                        my_components['dynamic_hit'] = ConditionalComponent('dynamic_hit', hit, dynamic)
                    elif component == 'dynamic_mt':
                        mt, dynamic = status.find('dynamic_mt').text.split(';')
                        my_components['dynamic_mt'] = ConditionalComponent('dynamic_mt', mt, dynamic)
                    elif component == 'weakness':
                        damage_type, num = status.find('weakness').text.split(',')
                        my_components['weakness'] = WeaknessComponent(damage_type, num)
                    # Others...
                    elif component == 'rescue':
                        my_components['rescue'] = RescueComponent()
                    elif component == 'count':
                        my_components['count'] = CountComponent(int(status.find('count').text))
                    elif component == 'tether':
                        my_components['tether'] = status.find('tether').text
                    elif component == 'vampire':
                        my_components['vampire'] = status.find('vampire').text
                    elif component == 'caretaker':
                        my_components['caretaker'] = int(status.find('caretaker').text)
                    elif component == 'remove_range':
                        my_components['remove_range'] = int(status.find('remove_range').text)
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
                    elif component == 'active':
                        charge = int(status.find('active').text)
                        my_components['active'] = getattr(ActiveSkill, s_id)(name, charge)
                    elif component == 'passive':
                        my_components['passive'] = getattr(ActiveSkill, s_id)(name)
                    elif component == 'aura':
                        aura_range = int(status.find('range').text)
                        child = status.find('child').text
                        target = status.find('target').text
                        my_components['aura'] = ActiveSkill.Aura(aura_range, target, child)
                    elif component == 'status_after_battle':
                        child = status.find('status_after_battle').text
                        my_components['status_after_battle'] = child
                    elif component == 'status_after_help':
                        child = status.find('status_after_help').text
                        my_components['status_after_help'] = child
                    elif component == 'status_on_complete':
                        child = status.find('status_on_complete').text
                        my_components['status_on_complete'] = child
                    elif component == 'ai':
                        ai = status.find('ai').text
                        my_components['ai'] = ai
                    else:
                        my_components[component] = True

                currentStatus = StatusObject(s_id, name, my_components, desc, icon_index)

                return currentStatus

def deserialize(s_dict, unit, gameStateObj):
    status = statusparser(s_dict['id'])
    #status = HandleStatusAddition(status, unit, gameStateObj)
    if s_dict['time_left']:
        status.time.time_left = s_dict['time_left']
    if s_dict.get('count') != None:
        status.count.count = s_dict['count']
    if s_dict['upkeep_sc_count']:
        status.upkeep_stat_change.count = s_dict['upkeep_sc_count']
    if s_dict['rhythm_sc_count']:
        status.rhythm_stat_change.count = s_dict['rhythm_sc_count']
    if s_dict.get('charge'):
        status.active.current_charge = s_dict['charge']
    if s_dict.get('children'):
        status.children = s_dict['children']
    if s_dict.get('parent_id'):
        status.parent_id = s_dict['parent_id']
    # For rescue
    if s_dict.get('rescue'):
        status.rescue.skl_penalty = int(s_dict['rescue'][0])
        status.rescue.spd_penalty = int(s_dict['rescue'][1])
    elif status.rescue:
        status.rescue.skl_penalty = -unit.stats['SKL'].base_stat/2
        status.rescue.spd_penalty = -unit.stats['SPD'].base_stat/2
    if status.passive:
        for item in unit.items:
            status.passive.apply_mod(item)
    unit.status_effects.append(status)

feat_list = ['fStrength +2', 'fMagic +2', 'fSkill +3', 'fSpeed +2', 'fDefense +2', 'fResistance +2', 'fMovement +1', 'fConstitution +3', 'fMaximum HP +5', 'fLuck +4']