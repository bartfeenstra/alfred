import abc
import importlib
from functools import reduce
from typing import Iterable, List

from contracts import contract, ContractsMeta, with_metaclass
from icu import Locale


@contract
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


def sanitize_phrase(phrase: str) -> str:
    return ' '.join(phrase.split()).lower()


class ValueObject(with_metaclass(ContractsMeta)):
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._do_eq(other)

    @contract
    def _do_eq(self, other: object) -> bool:
        return True

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return super().__repr__() + str(self)


class LocaleConfiguration(object):
    def __init__(self, default: Locale = None, outputs: Iterable[Locale] = None):
        if default is None:
            self._default = Locale('en_US')
        else:
            self._default = default
        if outputs is None:
            self._outputs = []
        else:
            self._outputs = outputs

    @property
    @contract
    def default(self) -> Locale:
        return self._default

    @property
    @contract
    def outputs(self) -> Iterable:
        if self._outputs:
            return self._outputs
        else:
            return [self.default]


class Configuration(object):
    # Read the schema, after composing it from the parts provided by plugins (maybe redefine what it means to be a plugin?)
    # Config property names are level_one.level_two.level3.propname
    # How do we create custom config classes from lists and dicts?
    def __init__(self, input_id: str,
                 output_id: str, call_signs: List[str],
                 global_interaction_ids:
                 List[str],
                 root_interaction_ids: List[str],
                 locale: LocaleConfiguration = None):
        self.call_signs = call_signs
        self.global_interaction_ids = global_interaction_ids
        self.input_id = input_id
        self.output_id = output_id
        self.root_interaction_ids = root_interaction_ids
        if locale is not None:
            self.locale = locale
        else:
            self.locale = LocaleConfiguration()


class Plugin(with_metaclass(ContractsMeta, object)):
    @property
    @contract
    def id(self) -> str:
        return qualname(self.__class__)


class Input(Plugin):
    @abc.abstractmethod
    @contract
    def listen(self) -> Iterable[str]:
        pass


class Output(Plugin):
    @abc.abstractmethod
    @contract
    def say(self, phrase: str):
        pass


class State(ValueObject):
    pass


class UnexpectedStateError(ValueError):
    def __init__(self, expected_type: type, actual: State):
        self._expected_type = expected_type
        self._actual = actual

    def __str__(self):
        return 'Expected interaction state of type %s, but got %s instead.' % (
        self._expected_type, self._actual.__class__)


class Interaction(Plugin):
    @property
    @abc.abstractmethod
    @contract
    def name(self) -> str:
        pass

    @abc.abstractmethod
    @contract
    def knows(self, phrase: str):
        """
        Returns state if the phrase is known, or None otherwise.
        :param phrase: str
        :return:
        """
        pass

    @abc.abstractmethod
    @contract
    def enter(self, state: State) -> State:
        """
        Enters a desired state, and returns the final state.
        :param state:
        :return:
        """
        pass

    @contract
    def get_interactions(self) -> Iterable['Interaction']:
        return []


class InteractionRequest(with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    @contract
    def request(self, state: State) -> State:
        pass


class InteractionObserver(with_metaclass(ContractsMeta, object)):
    @contract
    def pre_enter_interaction(self, interaction: Interaction,
                              state: State):
        pass

    @contract
    def post_enter_interaction(self, interaction: Interaction,
                               state: State,
                               available_interactions: List[Interaction]):
        pass


class Environment(InteractionObserver):
    def __init__(self, configuration: Configuration):
        self._plugins = PluginRepository(self)
        self._configuration = configuration
        self._output = self._plugins.get(
            configuration.output_id)  # type: ignore
        self._current_interaction = self._plugins.get(
            'alfred_speech.contrib.interactions.CallSign')  # type: ignore
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
    @contract
    def current_interaction(self) -> Interaction:
        return self._current_interaction

    @property
    @contract
    def available_interactions(self) -> List[Interaction]:
        return self._available_interactions

    def _set_available_interactions(self,
                                    interactions: List[Interaction] = None):
        if interactions is None:
            interactions = []
        self._available_interactions = interactions + list(
            map(self.plugins.get,
                self.configuration.global_interaction_ids))

    def post_enter_interaction(self, interaction: Interaction,
                               state: State,
                               available_interactions: List[Interaction]):
        self._current_interaction = interaction
        if available_interactions:
            self._set_available_interactions(available_interactions)


class Listener(object):
    def __init__(self, environment: Environment, input: Input):
        self._environment = environment
        self._observers = [environment]
        self._input = input

    def listen(self):
        for phrase in self._input.listen():
            interaction, state = self._find_interaction(
                sanitize_phrase(phrase))
            if interaction is not None:
                self._enter_interaction(interaction, state)

    @contract
    def _find_interaction(self, phrase: str):
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
    def __init__(self, environment: Environment):
        self._environment = environment

    @contract
    def get(self, name: str) -> Plugin:
        cls = get_class(name)

        # Instantiate the class.
        if issubclass(cls, EnvironmentAwareFactory):
            return cls.create(self._environment)  # type: ignore
        return cls()  # type: ignore
