from typing import Iterable, Optional, Tuple, List

import abc
import importlib
from contracts import contract


class Environment(object):
    @contract
    def __init__(self, input_id: str,
                 output_id: str, call_signs: List[str],
                 global_interaction_ids:
                 List[str],
                 root_interaction_ids: List[str]):
        self.call_signs = call_signs
        self.global_interaction_ids = global_interaction_ids
        self.input_id = input_id
        self.interactions = []
        self.plugins = PluginRepository(self)
        self.output_id = output_id
        self.output = self.plugins.get(output_id)
        self.root_interaction_ids = root_interaction_ids


class Plugin(object):
    @contract
    def __init__(self, environment: Environment):
        self._environment = environment

    @property
    def id(self) -> str:
        return self.__class__.__module__ + '.' + self.__class__.__name__


class Input(Plugin):
    @contract
    @abc.abstractmethod
    def listen(self) -> Iterable[str]:
        pass


class Output(Plugin):
    @contract
    @abc.abstractmethod
    def say(self, phrase: str):
        pass


class State(object):
    pass


class Interaction(Plugin):
    @property
    @contract
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def knows(self, phrase: str) -> Optional[State]:
        """
        Returns state if the phrase is known, or None otherwise.
        :param phrase: str
        :return:
        """
        pass

    @contract
    def enter(self, state: State) -> List[str]:
        pass


class PluginRepository(object):
    @contract
    def __init__(self, environment: Environment):
        self._environment = environment

    @contract
    def get(self, name: str) -> Plugin:
        module_name, class_name = name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls(self._environment)


class Listener(object):
    @contract
    def __init__(self, environment: Environment):
        self._environment = environment
        self._input = environment.plugins.get(environment.input_id)

    def listen(self):
        self._environment.interactions = list(map(self._environment.plugins.get,
                                                  self._environment.global_interaction_ids))  # noqa 501
        for phrase in self._input.listen():
            self.interact(phrase)

    @contract
    def interact(self, phrase: str):
        interaction, state = self._find_interaction(phrase)
        if interaction is not None:
            self._enter_interaction(interaction, state)

    def _find_interaction(self, phrase: str) -> Tuple[Optional[Interaction],
                                                      State]:
        for interaction in self._environment.interactions:
            state = interaction.knows(phrase)
            if isinstance(state, State):
                return interaction, state
        return None, State()

    @contract
    def _enter_interaction(self, interaction: Interaction, state: State):
        next_interaction_ids = interaction.enter(state)
        # If the interaction returned new interactions, update the
        # environment.
        if next_interaction_ids:
            self._environment.interactions = list(map(
                self._environment.plugins.get,
                next_interaction_ids +
                self._environment.global_interaction_ids))
