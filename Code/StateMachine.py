from . import GlobalConstants as GC
from . import InputManager, Engine

import logging
logger = logging.getLogger(__name__)

# === Finite State Machine Object ===============================
class StateMachine(object):

    def __init__(self, state_list=[], temp_state=[]):
        # All places where states could be hiding
        from . import GeneralStates, Transitions, PrepBase, OptionsMenu, \
            InfoMenu, UnitMenu, DebugMode, Turnwheel, Objective, \
            Overworld, LevelUp, Promotion
        self.all_states = {'free': GeneralStates.FreeState,
                           'turn_change': GeneralStates.TurnChangeState,
                           'move': GeneralStates.MoveState,
                           'optionsmenu': GeneralStates.OptionsMenuState,
                           'optionchild': GeneralStates.OptionChildState,
                           'weapon': GeneralStates.WeaponState,
                           'attack': GeneralStates.AttackState,
                           'phase_change': GeneralStates.PhaseChangeState,
                           'spell': GeneralStates.SpellState,
                           'item': GeneralStates.ItemState,
                           'itemchild': GeneralStates.ItemChildState,
                           'spellweapon': GeneralStates.SpellWeaponState,
                           'tileattack': GeneralStates.TileAttackState,
                           'movement': GeneralStates.MovementState,
                           'combat': GeneralStates.CombatState,
                           'move_camera': GeneralStates.CameraMoveState,
                           'canto_wait': GeneralStates.CantoWaitState,
                           'menu': GeneralStates.MenuState,
                           'select': GeneralStates.SelectState,
                           'skillselect': GeneralStates.SelectState,
                           'stealselect': GeneralStates.SelectState,
                           'tradeselect': GeneralStates.SelectState,
                           'takeselect': GeneralStates.SelectState,
                           'dropselect': GeneralStates.SelectState,
                           'giveselect': GeneralStates.SelectState,
                           'rescueselect': GeneralStates.SelectState,
                           'talkselect': GeneralStates.SelectState,
                           'supportselect': GeneralStates.SelectState,
                           'unlockselect': GeneralStates.SelectState,
                           'trade': GeneralStates.TradeState,
                           'steal': GeneralStates.StealState,
                           'repair': GeneralStates.RepairState,
                           'arena': GeneralStates.ArenaState,
                           'arena_base': GeneralStates.ArenaState,
                           'title_dialogue': Transitions.TitleDialogue,
                           'dialogue': GeneralStates.DialogueState,
                           'transparent_dialogue': GeneralStates.DialogueState,
                           'victory': GeneralStates.VictoryState,
                           'itemgain': GeneralStates.ItemGainState,
                           'itemdiscard': GeneralStates.ItemDiscardState,
                           'itemdiscardchild': GeneralStates.ItemDiscardChildState,
                           'dying': GeneralStates.DyingState,
                           'status': GeneralStates.StatusState,
                           'end_step': GeneralStates.StatusState,
                           'exp_gain': LevelUp.GainExpState,
                           'promotion_choice': Promotion.PromotionChoiceState,
                           'promotion': Promotion.PromotionState,
                           'feat_choice': GeneralStates.FeatChoiceState,
                           'ai': GeneralStates.AIState,
                           'vendor': GeneralStates.ShopState,
                           'armory': GeneralStates.ShopState,
                           'market': GeneralStates.ShopState,
                           'repair_shop': GeneralStates.RepairShopState,
                           'battle_save': GeneralStates.BattleSaveState,
                           'dialog_options': GeneralStates.DialogOptionsState,
                           'wait': GeneralStates.WaitState,
                           'minimap': GeneralStates.MinimapState,
                           'chapter_transition': Transitions.ChapterTransitionState,
                           'prep_main': PrepBase.PrepMainState,
                           'prep_pick_units': PrepBase.PrepPickUnitsState,
                           'prep_formation': PrepBase.PrepFormationState,
                           'prep_formation_select': PrepBase.PrepFormationSelectState,
                           'prep_items': PrepBase.PrepItemsState,
                           'prep_items_choices': PrepBase.PrepItemsChoicesState,
                           'prep_transfer': PrepBase.PrepTransferState,
                           'convoy_transfer': PrepBase.ConvoyTransferState,
                           'prep_list': PrepBase.PrepListState,
                           'prep_trade_select': PrepBase.PrepTradeSelectState,
                           'prep_trade': PrepBase.PrepTradeState,
                           'prep_use_item': PrepBase.PrepUseItemState,
                           'base_main': PrepBase.BaseMainState,
                           'base_items': PrepBase.PrepItemsState,
                           'base_info': PrepBase.BaseInfoState,
                           'base_support_convos': PrepBase.BaseSupportConvoState,
                           'base_codex_child': PrepBase.BaseCodexChildState,
                           'base_map': PrepBase.BaseMapState,
                           'base_library': PrepBase.BaseLibraryState,
                           'base_records': PrepBase.BaseRecordsState,
                           'base_armory_pick': PrepBase.PrepItemsState,
                           'base_market': PrepBase.BaseMarketState,
                           'base_arena_choice': PrepBase.BaseArenaState,
                           'start_start': Transitions.StartStart,
                           'start_option': Transitions.StartOption,
                           'start_load': Transitions.StartLoad,
                           'start_restart': Transitions.StartRestart,
                           'start_mode': Transitions.StartMode,
                           'start_new': Transitions.StartNew,
                           'start_newchild': Transitions.StartNewChild,
                           'start_extras': Transitions.StartExtras,
                           'start_all_saves': Transitions.StartAllSaves,
                           'start_preloaded_levels': Transitions.StartPreloadedLevels,
                           'start_wait': Transitions.StartWait,
                           'start_save': Transitions.StartSave,
                           'credits': Transitions.CreditsState,
                           'game_over': Transitions.GameOverState,
                           'transition_in': Transitions.TransitionInState,
                           'transition_out': Transitions.TransitionOutState,
                           'transition_pop': Transitions.TransitionPopState,
                           'transition_double_pop': Transitions.TransitionDoublePopState,
                           'transition_clean': Transitions.TransitionCleanState,
                           'config_menu': OptionsMenu.OptionsMenu,
                           'status_menu': Objective.StatusMenu,
                           'info_menu': InfoMenu.InfoMenu,
                           'unit_menu': UnitMenu.UnitMenu,
                           'turnwheel': Turnwheel.TurnwheelState,
                           'force_turnwheel': Turnwheel.TurnwheelState,
                           'overworld': Overworld.OverworldState,
                           'overworld_effects': Overworld.OverworldEffectsState,
                           'overworld_options': Overworld.OverworldOptionsState,
                           'debug': DebugMode.DebugState}
        self.state = []
        for state_name in state_list:
            self.state.append(self.all_states[state_name](state_name))
        self.temp_state = temp_state
        self.last_state = None

    def process_temp_state(self, gameStateObj, metaDataObj):
        if self.temp_state:
            logger.debug('Temp State: %s', self.temp_state)
        for state in self.temp_state:
            if state == 'pop':
                if self.state:
                    self.state[-1].finish(gameStateObj, metaDataObj)
                    self.state.pop()
            elif state == 'clear':
                for s in reversed(self.state):
                    if s.processed:
                        s.processed = False
                        s.end(gameStateObj, metaDataObj)
                    s.finish(gameStateObj, metaDataObj)
                self.state = []
            else:
                new_state = self.all_states[state](state)
                self.state.append(new_state)

        self.temp_state = []

    def changeState(self, newstate):
        self.temp_state.append(newstate)

    def back(self):
        self.temp_state.append('pop')

    def clear(self):
        self.temp_state.append('clear')

    def hard_clear(self):
        self.state = [self.state[-1]]

    def getState(self):
        if self.state:
            return self.state[-1].name

    def getPreviousState(self):
        if len(self.state) >= 2:
            return self.state[-2].name

    def get_under_state(self, state, under=1):
        idx = self.state.index(state)
        if idx > 0:
            return self.state[idx - under]
        else:
            return 0

    def get_last_state(self):
        return self.last_state

    def from_transition(self):
        return self.get_last_state() in ('transition_out', 'transition_pop', 'transition_double_pop', 'transition_clean')

    def inList(self, state_name):
        return any([state_name == state.name for state in self.state]) or any([state_name == temp_state for temp_state in self.temp_state])

    # Keeps track of the state at every tick
    def update(self, eventList, gameStateObj, metaDataObj):
        # print(self.state)
        time_start = Engine.get_true_time()
        state_name = self.state[-1].name
        repeat_flag = False # Determines whether we run the state machine again in the same frame
        # Is this a new state?
        if not self.state[-1].processed:
            self.state[-1].processed = True
            begin_output = self.state[-1].begin(gameStateObj, metaDataObj)
            if begin_output == 'repeat':
                repeat_flag = True
            self.state[-1].started = True
            self.last_state = self.state[-1].name
        time_input = Engine.get_true_time()
        if not repeat_flag:
            input_output = self.state[-1].take_input(eventList, gameStateObj, metaDataObj)
            time_upkeep = Engine.get_true_time() #
            update_output = self.state[-1].update(gameStateObj, metaDataObj)
            if input_output == 'repeat' or update_output == 'repeat':
                repeat_flag = True
        else:
            time_upkeep = time_input
        time_update = Engine.get_true_time()
        if not repeat_flag:
            mapSurf = self.state[-1].draw(gameStateObj, metaDataObj)
        else:  # Don't draw to surf, since we're gonna run through this again
            mapSurf = None
        time_draw = Engine.get_true_time()
        # Don't end if you are going to a transparent dialogue state
        if self.temp_state and not any(t_s == 'transparent_dialogue' for t_s in self.temp_state):
            self.state[-1].processed = False
            self.state[-1].end(gameStateObj, metaDataObj)
        # Process temp state
        self.process_temp_state(gameStateObj, metaDataObj)
        time_end = Engine.get_true_time()
        if time_end - time_start > 25:
            logger.debug('StateMachine took too long: %s Begin: %s, Input: %s, Update: %s, Draw: %s, End: %s', state_name,
                         time_input - time_start, time_upkeep - time_input, time_update - time_upkeep, time_draw - time_update, time_end - time_draw)
        return mapSurf, repeat_flag

    def begin(self):
        self.state[-1].begin()

    def serialize(self):
        return [state.name for state in self.state], self.temp_state

# https://stackoverflow.com/questions/6730128/python-how-to-register-all-child-classes-with-the-father-class-upon-creation
# class AutoRegister(type):
#     def __new__(mcs, name, bases, classdict):
#         new_cls = type.__new__(mcs, name, bases, classdict)
#         for b in bases:
#             if hasattr(b, 'register_subclass'):
#                 b.register_subclass(new_cls.name, new_cls)
#         return new_cls

class State(object):
    show_map = True

    def __init__(self, name='generic'):
        self.name = name
        self.processed = False
        self.started = False
        self.fluid_helper = InputManager.FluidScroll()

    def take_input(self, eventList, gameStateObj, metaDataObj):
        gameStateObj.input_manager.process_input(eventList)

    def begin(self, gameStateObj, metaDataObj):
        pass

    def end(self, gameStateObj, metaDataObj):
        pass

    def finish(self, gameStateObj, metaDataObj):
        pass

    def update(self, gameStateObj, metaDataObj):
        # Animate!
        if self.show_map:
            gameStateObj.cameraOffset.update(gameStateObj)
            gameStateObj.map.update(gameStateObj)
            gameStateObj.highlight_manager.update()
            for unit in gameStateObj.allunits:
                unit.update(gameStateObj)             
            gameStateObj.cursor.update(gameStateObj)
            for cursor in gameStateObj.fake_cursors:
                cursor.update(gameStateObj)
            for animation in gameStateObj.allanimations:
                animation.update(gameStateObj)
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.update()
        if gameStateObj.childMenu:
            gameStateObj.childMenu.update()

    def draw(self, gameStateObj, metaDataObj):
        if self.show_map and gameStateObj.map:
            mapSurf = gameStateObj.drawMap()  # Creates mapSurf
            gameStateObj.set_camera_limits()
            rect = (gameStateObj.cameraOffset.get_x()*GC.TILEWIDTH, gameStateObj.cameraOffset.get_y()*GC.TILEHEIGHT, GC.WINWIDTH, GC.WINHEIGHT)
            mapSurf = Engine.subsurface(mapSurf, rect)
            # Draw animations
            for animation in gameStateObj.allanimations:
                animation.draw(mapSurf, gameStateObj)
        else:
            mapSurf = gameStateObj.generic_surf
        if gameStateObj.background:
            if gameStateObj.background.draw(mapSurf):
                gameStateObj.background = None
        if gameStateObj.activeMenu:
            gameStateObj.activeMenu.draw(mapSurf, gameStateObj)
            if gameStateObj.childMenu:
                gameStateObj.childMenu.draw(mapSurf, gameStateObj)
        return mapSurf
