import datetime
import subprocess
from typing import Iterable, Sequence

import abc
import copy
import os
import re
import tempfile
from contracts import contract
from pocketsphinx import LiveSpeech


class Ear(object):
    @contract
    @abc.abstractmethod
    def listen(self) -> Iterable[str]:
        pass


class SphinxEar(Ear):
    def __init__(self):
        self._sphinx = LiveSpeech()

    @contract
    def listen(self) -> Iterable[str]:
        for phrase in self._sphinx:
            yield str(phrase)


class Mouth(object):
    @contract
    @abc.abstractmethod
    def say(self, phrase: str):
        pass


class Pico2WaveMouth(Mouth):
    @contract
    def say(self, phrase: str):
        path = self._create_file(phrase)
        self._play_file(path)
        self._remove_file(path)

    @contract
    def _create_file(self, phrase: str) -> str:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name

        cmd = ['pico2wave', '--wave', path, phrase]
        subprocess.call(cmd)
        return path

    @contract
    def _remove_file(self, path: str):
        os.remove(path)

    @contract()
    def _play_file(self, path: str):
        cmd = ['aplay', path]
        subprocess.call(cmd)


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


class CallSign(Command):
    def __init__(self, call_signs: Sequence[str], commands: Sequence[Command]):
        self._call_signs = call_signs
        self._commands = commands

    @contract
    def applies(self, phrase: str) -> bool:
        for call_sign in self._call_signs:
            match = re.search('(^| )%s($| )' % call_sign, phrase,
                              re.IGNORECASE)
            if match is not None:
                return True
        return False

    @contract
    def execute(self, phrase: str, context: Context):
        context.mouth.say('Yes?')

    @contract
    def get_context(self, context: Context) -> Context:
        context = copy.deepcopy(context)
        context.commands = self._commands
        context.commands.append(self)
        return context


class CurrentDate(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        key_phrases = [
            'what day is it',
            'what\'s today\'s date',
            'what is today\'s date',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return True
        return False

    @contract
    def execute(self, phrase: str, context: Context):
        now = datetime.datetime.now()
        months = {
            1: 'January',
            2: 'February',
            3: 'March',
            4: 'April',
            5: 'May',
            6: 'June',
            7: 'July',
            8: 'August',
            9: 'September',
            10: 'October',
            11: 'November',
            12: 'December',
        }
        context.mouth.say('It\'s %s %d.' % (months[now.month], now.day))


class CurrentTime(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        key_phrases = [
            'what time is it',
            'what\'s the time',
            'what is the time',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return True
        return False

    @contract
    def execute(self, phrase: str, context: Context):
        now = datetime.datetime.now()
        hour = now.hour
        if hour > 12:
            hour -= 12
        context.mouth.say('It is %d:%d.' % (hour, now.minute))


class Brain(object):
    @contract
    def __init__(self, ear: Ear, mouth: Mouth, call_signs,
                 attention_span: int):
        self._ear = ear
        self._mouth = mouth
        self._call_signs = call_signs
        self._attention_span = attention_span

    def listen(self):
        context = Context()
        context.commands = self._get_superglobal_commands()
        context.mouth = self._mouth
        while True:
            for phrase in self._ear.listen():
                print(phrase)
                context = self._run_command(phrase, context)

    def _run_command(self, phrase: str, context: Context) -> Context:
        for command in context.commands:
            if command.applies(phrase):
                command.execute(phrase, context)
                return command.get_context(context)
        return context

    def _get_global_commands(self) -> Sequence[Command]:
        return [
            CurrentDate(),
            CurrentTime(),
        ]

    def _get_superglobal_commands(self) -> Sequence[Command]:
        return [
            CallSign(self._call_signs, self._get_global_commands()),
        ]
