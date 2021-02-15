from . import configuration as cf
from . import Utility

import logging
logger = logging.getLogger(__name__)

# Called when a unit arrives on a tile
def arrive(unit, gameStateObj):
    if unit.position:
        pull_auras(unit, gameStateObj)

    for status in unit.status_effects:
        if status.aura:
            propagate_aura(unit, status, gameStateObj)

# Called when a unit leaves a tile
def leave(unit, gameStateObj):
    if unit.position:
        # Remove me from the effects of other auras
        for status in gameStateObj.grid_manager.get_aura_node(unit.position):
            status.aura.remove(unit, gameStateObj)

        # Remove my auras
        for status in unit.status_effects:
            if status.aura:
                release_aura(unit, status, gameStateObj)

# Get other auras like this aura
def repull_aura(unit, old_status, gameStateObj):
    if unit.position:
        for status in gameStateObj.grid_manager.get_aura_node(unit.position):
            if old_status.aura.child_id == status.aura.child_id:
                owner = gameStateObj.get_unit_from_id(status.owner_id)
                status.aura.apply(owner, unit, gameStateObj)

# Get other units auras
def pull_auras(unit, gameStateObj):
    if unit.position:
        for status in gameStateObj.grid_manager.get_aura_node(unit.position):
            owner = gameStateObj.get_unit_from_id(status.owner_id)
            status.aura.apply(owner, unit, gameStateObj)

# Apply my aura to other nearby units
def propagate_aura(unit, status, gameStateObj):
    if unit.position:
        gameStateObj.grid_manager.reset_aura(status)
        positions = Utility.find_manhattan_spheres(range(1, status.aura.aura_range + 1), unit.position)
        positions = [pos for pos in positions if gameStateObj.map.check_bounds(pos)]
        if cf.CONSTANTS['aura_los']:
            positions = Utility.line_of_sight([unit.position], positions, status.aura.aura_range, gameStateObj)
        for pos in positions:
            gameStateObj.grid_manager.add_aura_node(pos, status)
            other_unit = gameStateObj.grid_manager.get_unit_node(pos)
            if other_unit:
                # Does not overwrite
                status.aura.apply(unit, other_unit, gameStateObj)

def release_aura(unit, status, gameStateObj):
    for pos in gameStateObj.grid_manager.get_aura_positions(status):
        gameStateObj.grid_manager.remove_aura_node(pos, status)
        other_unit = gameStateObj.grid_manager.get_unit_node(pos)
        if other_unit:
            status.aura.remove(other_unit, gameStateObj)
            repull_aura(other_unit, status, gameStateObj)
    gameStateObj.grid_manager.reset_aura(status)

def update_grid_manager_on_load(unit, status, gameStateObj):
    gameStateObj.grid_manager.reset_aura(status)
    positions = Utility.find_manhattan_spheres(range(1, status.aura.aura_range + 1), unit.position)
    positions = [pos for pos in positions if gameStateObj.map.check_bounds(pos)]
    if cf.CONSTANTS['aura_los']:
        positions = Utility.line_of_sight([unit.position], positions, status.aura.aura_range, gameStateObj)
    for pos in positions:
        gameStateObj.grid_manager.add_aura_node(pos, status)

def add_aura_highlights(unit, gameStateObj):
    for status in unit.status_effects:
        if status.aura:
            positions = gameStateObj.grid_manager.get_aura_positions(status)
            for pos in positions:
                gameStateObj.highlight_manager.add_highlight(pos, 'aura', allow_overlap=True)

def remove_aura_highlights(unit, gameStateObj):
    gameStateObj.highlight_manager.remove_aura_highlights()

class Aura(object):
    def __init__(self, aura_range, target, child_id, gameStateObj):
        from . import StatusCatalog
        self.aura_range = int(aura_range)
        self.target = target
        self.child_id = child_id
        self.child_status = StatusCatalog.statusparser(child_id, gameStateObj)

    def apply(self, owner, unit, gameStateObj):
        from . import Action
        if (self.target == 'Ally' and owner.checkIfAlly(unit) and owner is not unit) or \
           (self.target == 'Enemy' and owner.checkIfEnemy(unit)):
            logger.debug('Applying Aura %s to %s at %s', self.child_status.name, unit.name, unit.position)
            Action.do(Action.AddStatus(unit, self.child_status), gameStateObj) 

    def remove(self, unit, gameStateObj):
        from . import Action
        Action.do(Action.RemoveStatus(unit, self.child_status, unit), gameStateObj)
        # Action.do(Action.RemoveStatus(unit, self.child_id, unit), gameStateObj)
