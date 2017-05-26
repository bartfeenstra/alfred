import datetime
from typing import Sequence

import copy
import re
from alfred.lights import dmx_get_values, dmx_set_values
from alfred_speech.core import Command, Context
from contracts import contract
from webcolors import name_to_hex


class CallSign(Command):
    def __init__(self, call_signs: Sequence[str], commands: Sequence[Command]):
        self._call_signs = call_signs
        self._commands = commands

    @property
    @contract
    def name(self) -> str:
        return self._call_signs[0]

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
        context.commands = self._commands + [self]
        return context


class Help(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        match = re.search('^help$', phrase,
                          re.IGNORECASE)
        return match is not None

    @property
    @contract
    def name(self) -> str:
        return 'help'

    @contract
    def execute(self, phrase: str, context: Context):
        def get_name(command: Command):
            return command.name

        names = list(map(get_name, context.commands))
        context.mouth.say('You have %d options: %s.' % (len(names), ', or, '
                                                                    ''.join(
            names)))


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

    @property
    @contract
    def name(self) -> str:
        return 'What day is it?'

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

    @property
    @contract
    def name(self) -> str:
        return 'What time is it?'

    @contract
    def execute(self, phrase: str, context: Context):
        now = datetime.datetime.now()
        hour = now.hour
        if hour > 12:
            hour -= 12
        context.mouth.say('It is %d:%d.' % (hour, now.minute))


class ChangeLights(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        for word in phrase.split():
            try:
                name_to_hex(word)
                return True
            except ValueError:
                pass
        return False

    @property
    @contract
    def name(self) -> str:
        return 'the name of a color'

    @contract
    def execute(self, phrase: str, context: Context):
        dmx_values = dmx_get_values()
        for word in phrase.split():
            try:
                color = name_to_hex(word)
                dmx_set_values(color, dmx_values['luminosity'])
            except ValueError:
                pass


class LightsOff(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        key_phrases = [
            '^off|dark$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return True
        return False

    @property
    @contract
    def name(self) -> str:
        return 'off'

    @contract
    def execute(self, phrase: str, context: Context):
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 0)


class LightsOn(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        key_phrases = [
            '^on|full|light|bright$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return True
        return False

    @property
    @contract
    def name(self) -> str:
        return 'on'

    @contract
    def execute(self, phrase: str, context: Context):
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 255)


class DimLights(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        key_phrases = [
            '^dim|damn$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return True
        return False

    @property
    @contract
    def name(self) -> str:
        return 'dim'

    @contract
    def execute(self, phrase: str, context: Context):
        dmx_values = dmx_get_values()
        luminosity = max(dmx_values['luminosity'] - 25, 0)
        dmx_set_values(dmx_values['color'], luminosity)


class BrightenLights(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        key_phrases = [
            '^bright(e|o)n|right in$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return True
        return False

    @property
    @contract
    def name(self) -> str:
        return 'brighten'

    @contract
    def execute(self, phrase: str, context: Context):
        dmx_values = dmx_get_values()
        luminosity = min(dmx_values['luminosity'] + 25, 255)
        dmx_set_values(dmx_values['color'], luminosity)


class Lights(Command):
    @contract
    def applies(self, phrase: str) -> bool:
        key_phrases = [
            '^(set|change)* *(the)* *(light|lights|lamp|lamps)+$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return True
        return False

    @property
    @contract
    def name(self) -> str:
        return 'lights'

    @contract
    def execute(self, phrase: str, context: Context):
        context.mouth.say(self.name)

    @contract
    def get_context(self, context: Context) -> Context:
        context = copy.deepcopy(context)
        context.commands = [
            DimLights(),
            BrightenLights(),
            LightsOn(),
            LightsOff(),
            # ChangeLights is last, because it matches a wide and varying
            # list of phrases.
            ChangeLights(),
        ]
        return context
