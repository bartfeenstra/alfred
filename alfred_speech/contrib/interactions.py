import datetime
from typing import Iterable, List

import re
from alfred.lights import dmx_get_values, dmx_set_values
from alfred_speech.core import Interaction, State, EnvironmentAwareFactory, \
    Environment, InteractionRequest, qualname, UnexpectedStateError
from webcolors import name_to_hex
from icu import Locale


class EnvironmentAwareInteraction(Interaction, EnvironmentAwareFactory):
    def __init__(self, environment: Environment):
        self._environment = environment

    @classmethod
    def create(cls, environment: Environment):
        return cls(environment)


class CallSign(EnvironmentAwareInteraction):
    @property
    def name(self) -> str:
        return self._environment.configuration.call_signs[0]

    def knows(self, phrase: str):
        for call_sign in self._environment.configuration.call_signs:
            match = re.search('(^| )%s($| )' % call_sign, phrase,
                              re.IGNORECASE)
            if match is not None:
                return State()
        return None

    def enter(self, state):
        self._environment.output.say('Yes?')
        return state

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
    def name(self) -> str:
        return 'Help'

    def enter(self, state):
        names = list(map(lambda interaction: interaction.name,
                         self._environment.available_interactions))
        self._environment.output.say(
            'You have %d options: %s.' % (len(names), ', or, '
                                                      ''.join(
                names)))
        return state


class SwitchOutputLocale(EnvironmentAwareInteraction):
    class SwitchOutputLocaleState(State):
        def __init__(self, selectable_locales: Iterable[Locale]):
            if not selectable_locales:
                raise ValueError('At least one selectable locale must be provided.')
            self._selectable_locales = selectable_locales

        def _do_eq(self, other):
            if len(self._selectable_locales) != len(other._selectable_locales):
                return False
            for locale, other_locale in zip(self._selectable_locales, other._selectable_locales):
                if locale.getBaseName() != other_locale.getBaseName():
                    print('NEMAN')
                    print(locale.getBaseName())
                    print(other_locale.getBaseName())
                    return False
            return True

        @property
        def selectable_locales(self):
            return self._selectable_locales

    @property
    def name(self) -> str:
        return 'Change locale'

    def knows(self, phrase: str):
        match = re.search('^(?:do you|can we)? ?(?:(?:speak|talk)(?: in)?|know) ?(?:the)? ?(\w+) ?(?:language)? ?(?:(?:to|with) (?:(?:each other)|me)|(?:together))?\W*$', phrase, re.IGNORECASE)
        language_input = match.group(1)
        selectable_locales = []
        if match is not None:
            for locale in self._environment.configuration.locale.outputs:
                if language_input.lower() == locale.getDisplayLanguage().lower():
                    selectable_locales.append(locale)
            if selectable_locales:
                return self.SwitchOutputLocaleState(selectable_locales)
        return None

    def enter(self, state):
        if not isinstance(state, self.SwitchOutputLocaleState):
            raise UnexpectedStateError(self.SwitchOutputLocaleState, state)
        if len(state.selectable_locales) > 1:
            request = self._environment.plugins.get(qualname(SwitchOutputLocaleRequest))
            request = SwitchOutputLocaleRequest(state.selectable_locales)
            self._environment.request(request)

        self._environment.configuration.locale = state.language_code + self._environment.configuration.locale[2:]
        return state


class MultipleChoiceRequest(InteractionRequest, EnvironmentAwareFactory):
    def __init__(self, environment: Environment, selectable_locales: List[Locale]):
        self._environment = environment
        if len(selectable_locales) < 2:
            raise ValueError('At least two selectable locales must be provided.')
        self._selectable_locales = selectable_locales



class SwitchOutputLocaleRequest(InteractionRequest, EnvironmentAwareFactory):
    def __init__(self, environment: Environment, selectable_locales: List[Locale]):
        self._environment = environment
        if len(selectable_locales) < 2:
            raise ValueError('At least two selectable locales must be provided.')
        self._selectable_locales = selectable_locales

    @property
    def selectable_locales(self):
        return self._selectable_locales


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
    def name(self) -> str:
        return 'What day is it?'

    def enter(self, state):
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
        return state


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
    def name(self) -> str:
        return 'What time is it?'

    def enter(self, state):
        now = datetime.datetime.now()
        hour = now.hour
        if hour > 12:
            hour -= 12
        self._environment.output.say('It is %d:%d.' % (hour, now.minute))
        return state


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
    def name(self) -> str:
        return 'the name of a color'

    def enter(self, state):
        if not isinstance(state, self.ChangeLightsState):
            raise UnexpectedStateError(self.ChangeLightsState, state)
        dmx_values = dmx_get_values()
        for word in state.phrase.split():
            try:
                color = name_to_hex(word)
                dmx_set_values(color, dmx_values['luminosity'])
            except ValueError:
                pass
        return state


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
    def name(self) -> str:
        return 'off'

    def enter(self, state):
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 0)
        return state


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
    def name(self) -> str:
        return 'on'

    def enter(self, state):
        dmx_values = dmx_get_values()
        dmx_set_values(dmx_values['color'], 255)
        return state


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
    def name(self) -> str:
        return 'dim'

    def enter(self, state):
        dmx_values = dmx_get_values()
        luminosity = max(dmx_values['luminosity'] - 25, 0)
        dmx_set_values(dmx_values['color'], luminosity)
        return state


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
    def name(self) -> str:
        return 'brighten'

    def enter(self, state):
        dmx_values = dmx_get_values()
        luminosity = min(dmx_values['luminosity'] + 25, 255)
        dmx_set_values(dmx_values['color'], luminosity)
        return state


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
    def name(self) -> str:
        return 'lights'

    def enter(self, state):
        self._environment.output.say(self.name)
        return state

    def get_interactions(self) -> Iterable[Interaction]:
        return list(map(self._environment.plugins.get,
                        [
                            'alfred_speech.contrib.interactions.DimLights',
                            'alfred_speech.contrib.interactions.BrightenLights',  # noqa: E501
                            'alfred_speech.contrib.interactions.LightsOn',
                            'alfred_speech.contrib.interactions.LightsOff',
                            # ChangeLights is last, because it matches a wide
                            # and varying list of phrases.
                            'alfred_speech.contrib.interactions.ChangeLights',
                        ]))
