from typing import Iterable
from unittest import TestCase

from alfred_speech.contrib.interactions import CallSign, Help, SwitchOutputLocale
from alfred_speech.contrib.outputs import ListOutput
from alfred_speech.core import State, Environment, Configuration, \
    Interaction, qualname, LocaleConfiguration
from icu import Locale


class InteractionTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self._setUpConfiguration()
        self._configuration = Configuration(
            self._input_id,
            self._output_id, self._call_signs, self._global_interaction_ids,
            self._root_interaction_ids, LocaleConfiguration(self._locale_default, self._locale_outputs))
        self._environment = Environment(self._configuration)

    def _setUpConfiguration(self):
        self._input_id = 'alfred_speech.contrib.inputs:ListInput'
        self._output_id = 'alfred_speech.contrib.outputs:NullOutput'
        self._call_signs = ['Hey', 'Alfred']
        self._global_interaction_ids = []
        self._root_interaction_ids = []
        self._locale_default = Locale('en-US')
        self._locale_outputs = []

    def assertKnows(self, state: State, speech: Iterable[str]):
        for phrase in speech:
            self.assertEqual(self._sut.knows(phrase), state, 'With phrase "%s".' % phrase)


class CallSignTest(InteractionTestCase):
    def setUp(self):
        super().setUp()
        self._sut = CallSign(self._environment)

    def testName(self):
        self.assertIsInstance(self._sut.name, str)

    def testKnows(self):
        self.assertKnows(State(), self._configuration.call_signs)

    def testEnter(self):
        self._sut.enter(State())

    def testGetInteractions(self):
        self.assertEqual(self._sut.get_interactions(), list(map(
            self._environment.plugins.get,
            self._environment.configuration.root_interaction_ids)))


class HelpTest(InteractionTestCase):
    class HelpTestInteraction(Interaction):
        def knows(self, phrase: str):
            if self.name == phrase:
                return State()
            return None

        def enter(self, state: State):
            pass

        def get_interactions(self) -> Iterable[Interaction]:
            return []

    class FooInteraction(HelpTestInteraction):
        @property
        def name(self) -> str:
            return 'Foo'

    class BarInteraction(HelpTestInteraction):
        @property
        def name(self) -> str:
            return 'Bar'

    class BazInteraction(HelpTestInteraction):
        @property
        def name(self) -> str:
            return 'Baz'

    def setUp(self):
        self._help_interaction_ids = [qualname(self.FooInteraction),
                                      qualname(self.BarInteraction),
                                      qualname(self.BazInteraction)]
        super().setUp()
        self._sut = Help(self._environment)

    def _setUpConfiguration(self):
        super()._setUpConfiguration()
        self._output_id = qualname(ListOutput)
        self._global_interaction_ids = self._help_interaction_ids

    def testName(self):
        self.assertIsInstance(self._sut.name, str)

    def testKnows(self):
        self.assertKnows(State(), ['help'])

    def testEnter(self):
        self._sut.enter(State())
        # Assert that the name of every available interaction appears in the
        # help output.
        for id in self._help_interaction_ids:
            present = False
            for phrase in self._environment.output:
                if self._environment.plugins.get(id).name in phrase:
                    present = True
            self.assertTrue(present)

    def testGetInteractions(self):
        # Confirm no new interactions are provided, so we know we do not
        # need extensive test coverage.
        self.assertEqual(self._sut.get_interactions(), [])


class SwitchOutputLocaleTest(InteractionTestCase):
    def setUp(self):
        super().setUp()
        self._sut = SwitchOutputLocale(self._environment)

    def _setUpConfiguration(self):
        super()._setUpConfiguration()
        self._locale_outputs = [Locale('de', 'DE'), Locale('nl'), Locale('en', 'IN'), Locale('en', 'US'), Locale('en', 'GB')]

    def testKnows(self):
        expected_state = SwitchOutputLocale.SwitchOutputLocaleState([Locale('en', 'IN'), Locale('en', 'US'), Locale('en', 'GB')])
        speech = [
            'Do you know English',
            'Do you speak English?',
            'Can we talk in English?',
            'Can we speak English together?',
            'Speak English',
            'Speak English to me!',
            'Do you know the English language?',
            'do you speak the english language',
        ]
        self.assertKnows(expected_state, speech)

    def testEnterWithUnknownLanguage(self):
        state = SwitchOutputLocale.SwitchOutputLocaleState(
            [Locale('en', 'IN'), Locale('en', 'US'), Locale('en', 'GB')])
        self._sut.enter(state)

    def testEnterWithMultipleLanguages(self):
        self.skipTest()
