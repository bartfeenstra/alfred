import datetime
from typing import Iterable

import re
from alfred.lights import dmx_get_values, dmx_set_values
from alfred_speech.core import Interaction, State, EnvironmentAwareFactory, \
    Environment
from contracts import contract
from webcolors import name_to_hex


class EnvironmentAwareInteraction(Interaction, EnvironmentAwareFactory):
    @contract
    def __init__(self, environment: Environment):
        self._environment = environment

    @classmethod
    def create(cls, environment: Environment):
        return cls(environment)


class CallSign(EnvironmentAwareInteraction):
    @property
    @contract
    def name(self) -> str:
        return self._environment.configuration.call_signs[0]

    def knows(self, phrase: str):
        for call_sign in self._environment.configuration.call_signs:
            match = re.search('(^| )%s($| )' % call_sign, phrase,
                              re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @contract
    def enter(self, state: State):
        self._environment.output.say('Yes?')

    @contract
    def get_interactions(self) -> Iterable[Interaction]:
        return list(map(self._environment.plugins.get,
                        self._environment.configuration.root_interaction_ids))


class Help(EnvironmentAwareInteraction):
    def knows(self, phrase: str):
        match = re.search('^help$', phrase,
                          re.IGNORECASE)
        if match is not None:
            return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'help'

    @contract
    def enter(self, state: State):
        names = list(map(lambda interaction: interaction.name,
                         self._environment.plugins))
        self._environment.output.say(
            'You have %d options: %s.' % (len(names), ', or, '
                                                      ''.join(
                names)))


class CurrentDate(EnvironmentAwareInteraction):
    def knows(self, phrase: str):
        key_phrases = [
            '(what|which) (day|date) is it',
            '(what is|what\'s) *(the|today\'s) *date',
            'what is today\'s date',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'What day is it?'

    @contract
    def enter(self, state: State):
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
        self._environment.output.say(
            'It\'s %s %d.' % (months[now.month], now.day))


class CurrentTime(EnvironmentAwareInteraction):
    def knows(self, phrase: str):
        key_phrases = [
            'what time is it',
            'what\'s the time',
            'what is the time',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'What time is it?'

    @contract
    def enter(self, state: State):
        now = datetime.datetime.now()
        hour = now.hour
        if hour > 12:
            hour -= 12
        self._environment.output.say('It is %d:%d.' % (hour, now.minute))


class ChangeLights(Interaction):
    class ChangeLightsState(State):
        def __init__(self, phrase: str):
            self.phrase = phrase

    def knows(self, phrase: str):
        for word in phrase.split():
            try:
                name_to_hex(word)
                return self.ChangeLightsState(phrase)
            except ValueError:
                pass
        return None

    @property
    @contract
    def name(self) -> str:
        return 'the name of a color'

    @contract
    def enter(self, state: ChangeLightsState):
        dmx_values = dmx_get_values()
        for word in state.phrase.split():
            try:
                color = name_to_hex(word)
                dmx_set_values(color, dmx_values['luminosity'])
            except ValueError:
                pass


class LightsOff(Interaction):
    def knows(self, phrase: str):
        key_phrases = [
            '^off|dark$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'off'

    @contract
    def enter(self, state: State):
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 0)


class LightsOn(Interaction):
    def knows(self, phrase: str):
        key_phrases = [
            '^on|full|light|bright$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'on'

    @contract
    def enter(self, state: State):
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 255)


class DimLights(Interaction):
    def knows(self, phrase: str):
        key_phrases = [
            '^dim|damn$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'dim'

    @contract
    def enter(self, state: State):
        dmx_values = dmx_get_values()
        luminosity = max(dmx_values['luminosity'] - 25, 0)
        dmx_set_values(dmx_values['color'], luminosity)


class BrightenLights(Interaction):
    def knows(self, phrase: str):
        key_phrases = [
            '^bright(e|o)n|right in$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'brighten'

    @contract
    def enter(self, state: State):
        dmx_values = dmx_get_values()
        luminosity = min(dmx_values['luminosity'] + 25, 255)
        dmx_set_values(dmx_values['color'], luminosity)


class Lights(EnvironmentAwareInteraction):
    def knows(self, phrase: str):
        key_phrases = [
            '^(set|change)* *(the)* *(light|lights|lamp|lamps)+$',
        ]
        for key_phrase in key_phrases:
            match = re.search('^%s$' % key_phrase, phrase, re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @property
    @contract
    def name(self) -> str:
        return 'lights'

    @contract
    def enter(self, state: State):
        self._environment.output.say(self.name)

    @contract
    def get_interactions(self) -> Iterable[Interaction]:
        return list(map(self._environment.plugins.get,
                    [
                        'alfred_speech.contrib.interactions.DimLights',
                        'alfred_speech.contrib.interactions.BrightenLights',
                        'alfred_speech.contrib.interactions.LightsOn',
                        'alfred_speech.contrib.interactions.LightsOff',
                        # ChangeLights is last, because it matches a wide and
                        # varying list of phrases.
                        'alfred_speech.contrib.interactions.ChangeLights',
                    ]))
