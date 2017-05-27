import datetime
from typing import Sequence, Optional

import re
from alfred.lights import dmx_get_values, dmx_set_values
from alfred_speech.core import Interaction, State
from contracts import contract
from webcolors import name_to_hex


class CallSign(Interaction):
    @property
    @contract
    def name(self) -> str:
        return self._environment.call_signs[0]

    def knows(self, phrase: str) -> Optional[State]:
        for call_sign in self._environment.call_signs:
            match = re.search('(^| )%s($| )' % call_sign, phrase,
                              re.IGNORECASE)
            if match is not None:
                return State()
        return None

    @contract
    def enter(self, state: State) -> Sequence[str]:
        self._environment.mouth.say('Yes?')
        return self._environment.root_interaction_ids


class Help(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
        def get_name(command: Interaction):
            return command.name

        names = list(map(get_name,
                         self._environment.interactions))
        self._environment.mouth.say(
            'You have %d options: %s.' % (len(names), ', or, '
                                                      ''.join(
                names)))
        return []


class CurrentDate(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
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
        self._environment.mouth.say(
            'It\'s %s %d.' % (months[now.month], now.day))
        return []


class CurrentTime(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
        now = datetime.datetime.now()
        hour = now.hour
        if hour > 12:
            hour -= 12
        self._environment.mouth.say('It is %d:%d.' % (hour, now.minute))
        return []


class ChangeLights(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
        for word in phrase.split():
            try:
                name_to_hex(word)
                state = State()
                state.phrase = phrase
                return state
            except ValueError:
                pass
        return None

    @property
    @contract
    def name(self) -> str:
        return 'the name of a color'

    @contract
    def enter(self, state: State) -> Sequence[str]:
        dmx_values = dmx_get_values()
        for word in state.phrase.split():
            try:
                color = name_to_hex(word)
                dmx_set_values(color, dmx_values['luminosity'])
            except ValueError:
                pass
        return []


class LightsOff(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 0)
        return []


class LightsOn(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 255)
        return []


class DimLights(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
        dmx_values = dmx_get_values()
        luminosity = max(dmx_values['luminosity'] - 25, 0)
        dmx_set_values(dmx_values['color'], luminosity)
        return []


class BrightenLights(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
        dmx_values = dmx_get_values()
        luminosity = min(dmx_values['luminosity'] + 25, 255)
        dmx_set_values(dmx_values['color'], luminosity)


class Lights(Interaction):
    def knows(self, phrase: str) -> Optional[State]:
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
    def enter(self, state: State) -> Sequence[str]:
        self._environment.mouth.say(self.name)
        return [
            'alfred_speech.contrib.interactions.DimLights',
            'alfred_speech.contrib.interactions.BrightenLights',
            'alfred_speech.contrib.interactions.LightsOn',
            'alfred_speech.contrib.interactions.LightsOff',
            # ChangeLights is last, because it matches a wide and varying
            # list of phrases.
            'alfred_speech.contrib.interactions.ChangeLights',
        ]
