from typing import Iterable, Optional, Tuple, List

import abc
import importlib
from contracts import contract


def qualname(cls) -> str:
    return cls.__module__ + '.' + cls.__qualname__


class Configuration(object):
    @contract
    def __init__(self, input_id: str,
                 output_id: str, call_signs: List[str],
                 global_interaction_ids:
                 List[str],
                 root_interaction_ids: List[str]):
        self.call_signs = call_signs
        self.global_interaction_ids = global_interaction_ids
        self.input_id = input_id
        self.output_id = output_id
        self.root_interaction_ids = root_interaction_ids


class Plugin(object):
    @property
    def id(self) -> str:
        return qualname(self.__class__)


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
    def knows(self, phrase: str):
        """
        Returns state if the phrase is known, or None otherwise.
        :param phrase: str
        :return:
        """
        pass

    @contract
    @abc.abstractmethod
    def enter(self, state: State):
        pass

    @contract
    def get_interactions(self) -> Iterable['Interaction']:
        return []


class InteractionObserver(object):
    def pre_enter_interaction(self, interaction: Interaction,
                              state: State):
        pass

    def post_enter_interaction(self, interaction: Interaction,
                               state: State,
                               available_interactions: List[Interaction]):
        pass


class Environment(InteractionObserver):
    @contract
    def __init__(self, configuration: Configuration):
        self._plugins = PluginRepository(self)
        self._configuration = configuration
        self._output = self._plugins.get(configuration.output_id)
        self._current_interaction = self._plugins.get(
            'alfred_speech.contrib.interactions.CallSign')
        self._set_available_interactions()

    @property
    @contract
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    @contract
    def output(self) -> Output:
        return self._output

    @property
    def plugins(self) -> 'PluginRepository':
        return self._plugins

    @property
    @contract
    def current_interaction(self) -> Interaction:
        return self._current_interaction

    @property
    @contract
    def available_interactions(self) -> List[Interaction]:
        return self._available_interactions

    def _set_available_interactions(self,
                                    interactions: List[Interaction] = []):
        self._available_interactions = interactions + list(
            map(self.plugins.get,
                self.configuration.global_interaction_ids))

    @contract
    def post_enter_interaction(self, current_interaction: Interaction,
                               state: State,
                               available_interactions: List[Interaction]):
        self._current_interaction = current_interaction
        if available_interactions:
            self._set_available_interactions(available_interactions)


class Listener(object):
    def __init__(self, environment: Environment, input: Input):
        self._environment = environment
        self._observers = [environment]
        self._input = input

    def listen(self):
        for phrase in self._input.listen():
            interaction, state = self._find_interaction(phrase)
            if interaction is not None:
                self._enter_interaction(interaction, state)

    def _find_interaction(self, phrase: str) -> Tuple[Optional[Interaction],
                                                      State]:
        for interaction in self._environment.available_interactions:
            state = interaction.knows(phrase)
            if isinstance(state, State):
                return interaction, state
        return None, State()

    @contract
    def _enter_interaction(self, interaction: Interaction, state: State):
        for observer in self._observers:
            observer.pre_enter_interaction(interaction, state)
        interaction.enter(state)
        available_interactions = interaction.get_interactions()
        for observer in self._observers:
            observer.post_enter_interaction(interaction, state,
                                            available_interactions)


class EnvironmentAwareFactory(object):
    @abc.abstractclassmethod
    def create(cls, environment: Environment):
        pass


class PluginRepository(object):
    @contract
    def __init__(self, environment: Environment):
        self._environment = environment

    @contract
    def get(self, name: str) -> Plugin:
        # Load the class.
        module_name, class_name = name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)

        # Instantiate the class.
        if issubclass(cls, EnvironmentAwareFactory):
            return cls.create(self._environment)
        return cls()
