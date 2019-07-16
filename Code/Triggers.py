from . import Utility

# === TRIGGER STUFF ===
class Trigger(object):
    def __init__(self):
        self.units = {}

    def add_unit(self, unit_id, pos1, pos2):
        if ',' in pos1:
            pos1 = tuple(int(n) for n in pos1.split(','))
        if ',' in pos2:
            pos2 = tuple(int(n) for n in pos2.split(','))
        self.units[unit_id] = (pos1, pos2)

def get_trigger_unit(unitLine, allunits, reinforceUnits):
    if ',' in unitLine[2]:
        position = tuple(int(n) for n in unitLine[2].split(','))
        for unit in allunits:
            if unit.position == position:
                return unit.id
    else:
        for unit in allunits:
            if unit.id == unitLine[2]:
                return unit.id
        for event_id, (unit_id, position) in reinforceUnits.items():
            if event_id == unitLine[2] or unit_id == unitLine[2]:
                return unit_id
    return None

def finalize_triggers(allunits, reinforceUnits, triggers, level_map):
    def set_spawn_position(unit, current_pos):
        unit.position = None
        if current_pos[0] >= level_map.width:
            spawn_pos = level_map.width - 1, Utility.clamp(current_pos[1], 0, level_map.height - 1)
        elif current_pos[1] >= level_map.height:
            spawn_pos = Utility.clamp(current_pos[0], 0, level_map.width - 1), level_map.height - 1
        elif current_pos[0] < 0:
            spawn_pos = 0, Utility.clamp(current_pos[1], 0, level_map.height - 1)
        elif current_pos[1] < 0:
            spawn_pos = Utility.clamp(current_pos[0], 0, level_map.width - 1), 0
        # I want to add this to reinforceUnits because if the trigger is not
        # activated for some reason, can still use unit manually
        reinforceUnits[unit.id] = (unit.id, spawn_pos)

    def determine_first_position(unit, trigger_list):
        current_pos = unit.position
        if current_pos:
            queue = [t for t in trigger_list]
            counter = 0
            while queue and counter < 10:
                start, end = queue.pop()
                if end == current_pos:  # Running up the chain
                    current_pos = start
                    counter = 0
                else:
                    queue.insert(0, (start, end))
                    counter += 1
            if current_pos not in level_map.tiles:
                set_spawn_position(unit, current_pos)        
            else:
                unit.position = current_pos
        else:
            for start, end in trigger_list:
                if start not in level_map.tiles:  # Running up the chain
                    set_spawn_position(unit, start)
                    break

    # create a new object with unit id as main and triggers in dict
    # This organizes all triggers to be organized by unit instead of by trigger name
    unit_triggers = {}
    for trigger_name, trigger in triggers.items():
        for unit_id, (start, end) in trigger.units.items():
            if unit_id not in unit_triggers:
                unit_triggers[unit_id] = []
            unit_triggers[unit_id].append((start, end))

    # Now for each unit id in unit_triggers, set the position correctly
    for unit_id, trigger_list in unit_triggers.items():
        for unit in allunits:
            if unit_id == unit.id:
                determine_first_position(unit, trigger_list)
                break
