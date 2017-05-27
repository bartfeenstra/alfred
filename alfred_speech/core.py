from typing import Iterable, Sequence, Optional, Tuple

import abc
import importlib
from contracts import contract


class Ear(object):
    @contract
    @abc.abstractmethod
    def listen(self) -> Iterable[str]:
        pass


class Mouth(object):
    @contract
    @abc.abstractmethod
    def say(self, phrase: str):
        pass


class State(object):
    pass


class Environment(object):
    @contract
    def __init__(self,
                 mouth: Mouth, call_signs: Sequence[str],
                 global_interaction_ids:
                 Sequence[str],
                 root_interaction_ids: Sequence[str]):
        self.mouth = mouth
        self.global_interaction_ids = global_interaction_ids
        self.root_interaction_ids = root_interaction_ids
        self.call_signs = call_signs
        self.interactions = []


class Listener(object):
    @contract
    def __init__(self, ear: Ear, environment: Environment):
        self._ear = ear
        self._environment = environment
        self._interactions = InteractionRepository(environment)

    def listen(self):
        while True:
            self._environment.interactions = list(map(self._interactions.get,
                                                 self._environment.global_interaction_ids))
            for phrase in self._ear.listen():
                print(phrase)
                self._interact(phrase)

    @contract
    def _interact(self, phrase: str):
        for interaction in self._environment.interactions:
            state = interaction.knows(phrase)
            if isinstance(state, State):
                next_interaction_ids = interaction.enter(state)
                # If the interaction returned new interactions, update the
                # environment.
                if next_interaction_ids:
                    self._environment.interactions =list(map(
                        self._interactions.get,
                        next_interaction_ids +
                        self._environment.global_interaction_ids))
                return
        return


class Interaction(object):
    @contract
    def __init__(self, environment: Environment):
        self._environment = environment

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
    def enter(self, state: State) -> Tuple[str]:
        pass


class InteractionRepository(object):
    def __init__(self, environment: Environment):
        self._environment = environment
        self._interactions = {}

    @contract
    def get(self, id: str) -> Interaction:
        if id in self._interactions:
            return self._interactions[id]
        module_name, class_name = id.rsplit('.', 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        self._interactions[id] = cls(self._environment)
        return self._interactions[id]
