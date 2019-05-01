# === Imports ==================================================================
# Custom imports
try:
    import GlobalConstants as GC
    import configuration as cf
    import CustomObjects, ActiveSkill, Interaction, InfoMenu
    import UnitObject, Aura, Action, Utility, Engine
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import CustomObjects, ActiveSkill, Interaction, InfoMenu
    from . import UnitObject, Aura, Action, Utility, Engine

import logging
logger = logging.getLogger(__name__)

# === New Status Object ========================================================
class StatusObject(object):
    next_uid = 100

    def __init__(self, s_id, name, components, desc, image_index=None):
        self.uid = StatusObject.next_uid
        StatusObject.next_uid += 1
        self.id = s_id
        self.name = name
        self.desc = desc
        self.image_index = image_index or (0, 0)

        self.children = set()

        # Creates component slots
        self.components = components # Consumable, Weapon, Spell Bigger Picture
        for component_key, component_value in self.components.items():
            self.__dict__[component_key] = component_value

        self.loadSprites()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

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
        if self.active and self.active.item:
            self.active.item.removeSprites()

    def loadSprites(self):
        self.image = Engine.subsurface(GC.ITEMDICT['Skills'], (16*self.image_index[0], 16*self.image_index[1], 16, 16)) if self.image_index else None
        self.cooldown = GC.IMAGESDICT['IconCooldown']
        if self.upkeep_animation:
            self.upkeep_animation.loadSprites()
        if self.always_animation:
            self.always_animation.loadSprites()
        if self.active and self.active.item:
            self.active.item.loadSprites()
        self.help_box = None

    def serialize(self):
        serial_dict = {}
        serial_dict['uid'] = self.uid
        serial_dict['id'] = self.id
        serial_dict['time_left'] = self.time.time_left if self.time else None
        serial_dict['upkeep_sc_count'] = self.upkeep_stat_change.count if self.upkeep_stat_change else None
        serial_dict['rhythm_sc_count'] = self.rhythm_stat_change.count if self.rhythm_stat_change else None
        serial_dict['charge'] = self.active.current_charge if self.active else None
        serial_dict['children'] = self.children
        serial_dict['parent_id'] = self.parent_id
        serial_dict['count'] = self.count.count if self.count else None
        if self.rescue:
            serial_dict['rescue'] = self.rescue.penalties
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
            return super(StatusObject, self).__getattr__(attr)
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

class RhythmStatChangeComponent(object):
    def __init__(self, change, reset, init_count, limit):
        self.change = change
        self.count = init_count
        self.limit = limit
        self.reset = reset

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

class WeaknessComponent(object):
    def __init__(self, damage_type, num):
        self.damage_type = damage_type
        self.num = num

class RescueComponent(object):
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
                    HandleStatusRemoval(self.current_status, self.current_unit, gameStateObj)
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
        p_unit = gameStateObj.get_unit_from_id(status.parent_id)
        if not p_unit or not p_unit.position or not unit.position or Utility.calculate_distance(p_unit.position, unit.position) > status.remove_range:
            return "Remove"

    if status.hp_percentage:
        hp_change = int(int(unit.stats['HP']) * status.hp_percentage.percentage/100.0)
        old_hp = unit.currenthp
        Action.do(Action.ChangeHP(unit, hp_change), gameStateObj)
        if unit.currenthp > old_hp:
            GC.SOUNDDICT['MapHeal'].play()

    if status.upkeep_stat_change:
        Action.do(Action.ApplyStatChange(unit, status.upkeep_stat_change.stat_change), gameStateObj)
        Action.do(Action.ChangeStatusCount(status.upkeep_stat_change, status.upkeep_stat_change.count + 1), gameStateObj)

    if status.rhythm_stat_change:
        Action.do(Action.ChangeStatusCount(status.rhythm_stat_change, status.rhythm_stat_change.count + 1), gameStateObj)
        if status.rhythm_stat_change.count > status.rhythm_stat_change.limit:
            Action.do(Action.ChangeStatusCount(status.rhythm_stat_change, 0), gameStateObj)
            Action.do(Action.ApplyStatChange(unit, status.rhythm_stat_change.reset), gameStateObj)
        else:
            Action.do(Action.ApplyStatChange(unit, status.rhythm_stat_change.change), gameStateObj)

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

    if status.endstep_rhythm_stat_change:
        Action.do(Action.ChangeStatusCount(status.endstep_rhythm_stat_change, status.endstep_rhythm_stat_change.count + 1), gameStateObj)
        if status.endstep_rhythm_stat_change.count > status.endstep_rhythm_stat_change.limit:
            Action.do(Action.ChangeStatusCount(status.endstep_rhythm_stat_change, 0), gameStateObj)
            Action.do(Action.ApplyStatChange(unit, status.endstep_rhythm_stat_change.reset), gameStateObj)
        else:
            Action.do(Action.ApplyStatChange(unit, status.endstep_rhythm_stat_change.change), gameStateObj)

    if status.lost_on_endstep:
        HandleStatusRemoval(status, unit, gameStateObj)

    return oldhp, unit.currenthp

def HandleStatusAddition(status, unit, gameStateObj):
    if not isinstance(unit, UnitObject.UnitObject):
        return
    logger.info('Adding Status %s to %s at %s', status.id, unit.name, unit.position)
    # Check to see if we need to remove other statuses
    if not status.stack:
        # If this is a status that doesn't say it stacks, remove older versions of it
        for other_status in unit.status_effects:
            if other_status.id == status.id:
                logger.info('Status %s already present', status.id)
                if status.time or status.remove_range:
                    HandleStatusRemoval(other_status, unit, gameStateObj)
                else:
                    return # Just ignore this new one

    # Check to see if we should reflect this status back at user
    if 'reflect' in unit.status_bundle and not status.already_reflected and status.parent_id and not status.aura_child:
        p_unit = gameStateObj.get_unit_from_id(status.parent_id)
        s_copy = statusparser(status.id) # Create a copy of this status
        s_copy.parent_id = unit.id
        s_copy.already_reflected = True # So we don't get infinite reflections between two units with reflect
        HandleStatusAddition(s_copy, p_unit, gameStateObj)
           
    if not status.momentary:
        gameStateObj.add_status(status)  
        Action.do(Action.GiveStatus(unit, status), gameStateObj)

    # --- Momentary status ---
    # Momentary status do need to be worked with Actions
    # Since they can't be obviously reversed otherwise
    if status.convert:
        status.original_team = unit.team
        p_unit = gameStateObj.get_unit_from_id(status.parent_id)
        Action.do(Action.ChangeTeams(unit, p_unit.team), gameStateObj)

    if status.ai_change:
        status.original_ai = unit.ai_descriptor
        Action.do(Action.ChangeAI(unit, status.ai_change), gameStateObj)

    if status.refresh:
        Action.do(Action.Reset(unit), gameStateObj)
        # Automatic skills can also show up after being refreshed
        for status in unit.status_effects:
            check_automatic(status, unit, gameStateObj)

    if status.skill_restore:
        Action.do(Action.ChargeAllSkills(unit, 1000), gameStateObj)

    if status.clear:
        for status in unit.status_effects:
            if status.time:
                HandleStatusRemoval(status, unit, gameStateObj)

    # --- Non-momentary status ---
    if status.stat_change:
        Action.do(Action.ApplyStatChange(unit, status.stat_change), gameStateObj)
    if status.growth_mod:
        Action.do(Action.ApplyGrowthMod(unit, status.growth_mod), gameStateObj)

    if status.rescue:
        # Rescue penalty
        for idx, stat in enumerate(status.rescue.stats):
            status.rescue.penalties[idx] = -unit.stats[stat].base_stat//2
            unit.stats[stat].bonuses += status.rescue.penalties[idx]

    if status.name == "Clumsy":
        if 'horsemanship' in unit.status_bundle:
            HandleStatusRemoval(status, unit, gameStateObj)
    if status.horsemanship:
        for status in unit.status_effects:
            if status.name == "Clumsy":
                HandleStatusRemoval(status, unit, gameStateObj)

    if status.remove_tag:
        Action.do(Action.RemoveTag(status.remove_tag, unit), gameStateObj)

    if status.flying:
        unit.remove_tile_status(gameStateObj, force=True)
        
    if status.passive:
        for item in unit.items:
            status.passive.apply_mod(item)

    if status.aura:
        status.aura.set_parent_unit(unit)
        # Re-arrive at where you are at so you can give your friendos their status
        unit.propagate_aura(status.aura, gameStateObj)

    # These can't be easily reversed
    # when you gain shrugg off, lower negative status ailments to 0
    if status.shrug_off:
        for status in unit.status_effects:
            if status.time and status.negative and status.time.time_left > 1:
                Action.do(Action.ShrugOff(status), gameStateObj)

    # If you have shrug off, lower this ailment, if temporary, to 0
    if 'shrug_off' in unit.status_bundle:
        if status.time and status.time > 1:
            Action.do(Action.ShrugOff(status), gameStateObj)

    if status.affects_movement:
        if unit.team.startswith('enemy'):
            gameStateObj.boundary_manager._remove_unit(unit, gameStateObj)
            if unit.position:
                gameStateObj.boundary_manager._add_unit(unit, gameStateObj)

    # Status Always Animations are handle by the unit themselves, in their draw function they look at the 
    # current status effects affecting them and check if any have always animations. If they do, they draw them...
    return status

def HandleStatusRemoval(status, unit, gameStateObj, clean_up=False):
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
        Action.do(Action.TakeStatus(unit, status), gameStateObj)
        
    else:
        logger.warning('Status %s %s not present...', status.id, status.name)
        logger.warning(unit.status_effects)
        return
    if status.convert:
        Action.do(Action.ChangeTeams(unit, status.original_team), gameStateObj)
    if status.ai_change:
        Action.do(Action.ChangeAI(unit, status.original_ai), gameStateObj)
        
    if status.upkeep_stat_change:
        # unit.apply_stat_change([-stat*(status.upkeep_stat_change.count) for stat in status.upkeep_stat_change.stat_change])
        Action.do(Action.ApplyStatChange(unit, [-stat*(status.upkeep_stat_change.count) for stat in status.upkeep_stat_change.stat_change]), gameStateObj)
    if status.stat_change:
        # unit.apply_stat_change([-stat for stat in status.stat_change])
        Action.do(Action.ApplyStatChange(unit, [-stat for stat in status.stat_change]), gameStateObj)
    if status.growth_mod:
        Action.do(Action.ApplyGrowthMod(unit, [-growth for growth in status.growth_mod]), gameStateObj)
    if status.rescue:
        for idx, stat in enumerate(status.rescue.stats):
            unit.stats[stat].bonuses -= status.rescue.penalties[idx]
    if status.remove_tag:
        Action.do(Action.AddTag(status.remove_tag, unit), gameStateObj)
    if status.flying and not clean_up:
        unit.acquire_tile_status(gameStateObj, force=True)
    if status.passive:
        for item in unit.items:
            status.passive.reverse_mod(item)
    # Tell the parent status that it is not connected to me anymore
    if status.aura_child:
        status.parent_status.remove_child(unit)
    if status.tether:
        Action.do(Action.UnTetherStatus(status), gameStateObj)
    if status.status_on_complete and not clean_up:
        status_obj = statusparser(status.status_on_complete)
        HandleStatusAddition(status_obj, unit, gameStateObj)
    if status.ephemeral:
        unit.isDying = True
        # unit.set_hp(0)
        Action.do(Action.ChangeHP(unit, -10000), gameStateObj)
        gameStateObj.stateMachine.changeState('dying')
    if status.affects_movement:
        if unit.team.startswith('enemy'):
            gameStateObj.boundary_manager._remove_unit(unit, gameStateObj)
            if unit.position:
                gameStateObj.boundary_manager._add_unit(unit, gameStateObj)

# === STATUS PARSER ======================================================
# Takes one status id, as well as the database of status data, and outputs a status object.
def statusparser(s_id):
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
                elif component == 'rhythm_stat_change':
                    change, reset, init_count, limit = status.find('rhythm_stat_change').text.split(';')
                    change = Utility.intify_comma_list(change)
                    change.extend([0] * (cf.CONSTANTS['num_stats'] - len(change)))
                    reset = Utility.intify_comma_list(reset)
                    init_count = int(init_count)
                    limit = int(limit)
                    my_components['rhythm_stat_change'] = RhythmStatChangeComponent(change, reset, init_count, limit)
                elif component == 'endstep_rhythm_stat_change':
                    change, reset, init_count, limit = status.find('endstep_rhythm_stat_change').text.split(';')
                    change = Utility.intify_comma_list(change)
                    change.extend([0] * (cf.CONSTANTS['num_stats'] - len(change)))
                    reset = Utility.intify_comma_list(reset)
                    init_count = int(init_count)
                    limit = int(limit)
                    my_components['endstep_rhythm_stat_change'] = RhythmStatChangeComponent(change, reset, init_count, limit)
                # Combat changes
                elif component.startswith('conditional_'):
                    value, conditional = status.find(component).text.split(';')
                    my_components[component] = ConditionalComponent(component, value, conditional)
                elif component == 'weakness':
                    damage_type, num = status.find('weakness').text.split(',')
                    my_components['weakness'] = WeaknessComponent(damage_type, num)
                # Others...
                elif component == 'rescue':
                    my_components['rescue'] = RescueComponent(status.find('rescue').text)
                elif component == 'count':
                    my_components['count'] = CountComponent(int(status.find('count').text))
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
                elif component == 'unit_tint':
                    info_line = status.find('unit_tint').text
                    my_components['unit_tint'] = UnitTintComponent(info_line)
                elif component == 'active':
                    charge = int(status.find('active').text)
                    try:
                        my_components['active'] = getattr(ActiveSkill, s_id)(name, charge)
                    except AttributeError as e:
                        print("AttributeError %s. Missing ActiveSkill %s (not your fault)" % (e, name))
                elif component == 'automatic':
                    charge = int(status.find('automatic').text)
                    status_id = status.find('status').text
                    my_components['automatic'] = ActiveSkill.AutomaticSkill(name, charge, status_id)
                elif component == 'passive':
                    my_components['passive'] = getattr(ActiveSkill, s_id)(name)
                elif component == 'aura':
                    aura_range = int(status.find('range').text)
                    child = status.find('child').text
                    target = status.find('target').text
                    my_components['aura'] = Aura.Aura(aura_range, target, child)
                elif status.find(component) is not None and status.find(component).text:
                    my_components[component] = status.find(component).text
                else:
                    my_components[component] = True

            currentStatus = StatusObject(s_id, name, my_components, desc, image_index)

            return currentStatus

def deserialize(s_dict):
    status = statusparser(s_dict['id'])
    if not status:
        return
    status.uid = s_dict['uid']

    if s_dict['time_left']:
        status.time.time_left = s_dict['time_left']
    if s_dict.get('count') is not None:
        status.count.count = s_dict['count']
    if s_dict['upkeep_sc_count']:
        status.upkeep_stat_change.count = s_dict['upkeep_sc_count']
    if s_dict['rhythm_sc_count']:
        status.rhythm_stat_change.count = s_dict['rhythm_sc_count']
    if s_dict.get('charge'):
        status.active.current_charge = s_dict['charge']
    if s_dict.get('children'):
        status.children = set(s_dict['children'])
    if s_dict.get('parent_id'):
        status.parent_id = s_dict['parent_id']

    return status

def attach_to_unit(status, unit):
    """
    Done (on load) after loading both the unit and the status to attach 
    the status correctly to the unit after a suspend.
    """
    if status.aura:
        status.aura.set_parent_unit(unit)    
    if status.rescue:
        for idx, stat in enumerate(status.rescue.stats):
            status.rescue.penalties[idx] = -unit.stats[stat].base_stat//2
    if status.passive:
        for item in unit.items:
            status.passive.apply_mod(item)
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
