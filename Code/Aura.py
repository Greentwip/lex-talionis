try:
    import StatusObject
except ImportError:
    from . import StatusObject

import logging
logger = logging.getLogger(__name__)

class Aura(object):
    def __init__(self, aura_range, target, child):
        self.aura_range = int(aura_range)
        self.child = child
        self.child_status = StatusObject.statusparser(child)
        self.child_status.parent_status = self
        self.target = target
        self.children = set()

    def set_parent_unit(self, parent_unit):
        self.parent_unit = parent_unit
        self.child_status.parent_id = parent_unit.id

    def remove_child(self, affected_unit):
        logger.debug("Aura parent is removing a child.")
        l_c = len(self.children)
        self.children.discard(affected_unit.id)
        if l_c == len(self.children):
            print("Remove Child did not work!", affected_unit.name, affected_unit.position)
            print(self.children)

    def apply(self, unit, gameStateObj):
        if (self.target == 'Ally' and self.parent_unit.checkIfAlly(unit) and self.parent_unit is not unit) or \
           (self.target == 'Enemy' and self.parent_unit.checkIfEnemy(unit)):
            success = StatusObject.HandleStatusAddition(self.child_status, unit, gameStateObj)
            if success:
                self.children.add(unit.id)
                logger.debug('Applying Aura %s to %s at %s', self.child_status.name, unit.name, unit.position)

    def remove(self, unit, gameStateObj):
        if unit.id in self.children:
            StatusObject.HandleStatusRemoval(self.child_status, unit, gameStateObj)
            # HandleStatusRemoval handles remove unit id from self.children
