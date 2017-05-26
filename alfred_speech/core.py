from typing import Iterable

import abc
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


class Context(object):
    def __init__(self):
        self.commands = []
        self.mouth = None


class Command(object):
    @contract
    @abc.abstractmethod
    def applies(self, phrase: str) -> bool:
        pass

    @contract
    def execute(self, phrase: str, context: Context):
        pass

    @contract
    def get_context(self, context: Context) -> Context:
        return context


class Brain(object):
    @contract
    def __init__(self, ear: Ear,
                 global_context: Context):
        self._ear = ear
        self._global_context = global_context

    def listen(self):
        while True:
            context = self._global_context
            for phrase in self._ear.listen():
                print(phrase)
                context = self._create_context(self._run_command(phrase,
                                                                 context))

    @contract
    def _create_context(self, context: Context) -> Context:
        context.commands += self._global_context.commands
        context.mouth = self._global_context.mouth
        return context

    @contract
    def _run_command(self, phrase: str, context: Context) -> Context:
        for command in context.commands:
            if command.applies(phrase):
                command.execute(phrase, context)
                return command.get_context(context)
        return context
