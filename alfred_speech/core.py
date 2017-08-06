from typing import Iterable, Optional, Tuple, List

import abc
import importlib
from functools import reduce


def qualname(cls) -> str:
    return cls.__module__ + ':' + cls.__qualname__


def get_class(name: str) -> object:
    # Inner classes are supported by separating their module and qualified
    # class names by a colon (:). Example: "foo.bar:OuterClass.InnerClass".
    if -1 != name.find(':'):
        module_name, class_name = name.split(':', 1)
    # Alternatively, 'Django-style' class names supports loading outer
    # classes only. Example: "foo.bar.OuterClass".
    elif -1 != name.find('.'):
        module_name, class_name = name.rsplit('.', 1)
    else:
        raise ValueError(
            '"%s" is not a valid globally qualified class name. Module and '
            'class name segments must be separated by periods. The module and '
            'class names must be separated from each other using a colon or a '
            'period (for outer classes only).' % name)
    module = importlib.import_module(module_name)
    return reduce(lambda parent, class_name: getattr(parent, class_name),
                  class_name.split('.'), module)


class ComparableValueObject(object):
    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        return self.__dict__ == other.__dict__


class Configuration(object):
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
    @abc.abstractmethod
    def listen(self) -> Iterable[str]:
        pass


class Output(Plugin):
    @abc.abstractmethod
    def say(self, phrase: str):
        pass


class State(ComparableValueObject):
    pass


class Interaction(Plugin):
    @property
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

    @abc.abstractmethod
    def enter(self, state: State):
        pass

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
    def __init__(self, configuration: Configuration):
        self._plugins = PluginRepository(self)
        self._configuration = configuration
        self._output = self._plugins.get(configuration.output_id)
        self._current_interaction = self._plugins.get(
            'alfred_speech.contrib.interactions.CallSign')
        self._set_available_interactions()

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    def output(self) -> Output:
        return self._output

    @property
    def plugins(self) -> 'PluginRepository':
        return self._plugins

    @property
    def current_interaction(self) -> Interaction:
        return self._current_interaction

    @property
    def available_interactions(self) -> List[Interaction]:
        return self._available_interactions

    def _set_available_interactions(self,
                                    interactions: List[Interaction] = []):
        self._available_interactions = interactions + list(
            map(self.plugins.get,
                self.configuration.global_interaction_ids))

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
    def __init__(self, environment: Environment):
        self._environment = environment

    def get(self, name: str) -> Plugin:
        cls = get_class(name)

        # Instantiate the class.
        if issubclass(cls, EnvironmentAwareFactory):
            return cls.create(self._environment)
        return cls()
