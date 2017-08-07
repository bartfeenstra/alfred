from typing import Iterable
from unittest import TestCase, mock

from alfred_speech.contrib.interactions import EnvironmentAwareInteraction
from alfred_speech.core import PluginRepository, Environment, \
    Plugin, \
    qualname, EnvironmentAwareFactory, Configuration, Interaction, Listener, \
    State, get_class


class QualnameTest(TestCase):
    class NamedClass(object):
        pass

    def test(self):
        self.assertEqual(qualname(self.NamedClass),
                         'alfred_speech.tests.test_core:QualnameTest'
                         '.NamedClass')


class GetClassTest(TestCase):
    class LoadableClass(object):
        pass

    def testSuccess(self):
        self.assertEqual(get_class(
            'alfred_speech.tests.test_core:GetClassTest.LoadableClass'),
            self.LoadableClass)

    def testInvalidName(self):
        with self.assertRaises(ValueError):
            get_class('foo-bar')


class PluginRepositoryTest(TestCase):
    def setUp(self):
        super().setUp()

        self._environment = mock.Mock(Environment)

        self._sut = PluginRepository(self._environment)

    def testGetPluginWithoutFactory(self):
        self.assertIsInstance(self._sut.get(
            qualname(PluginWithoutFactory)),
            PluginWithoutFactory)

    def testGetPluginWithFactory(self):
        self.assertIsInstance(
            self._sut.get(qualname(PluginWithFactory)),
            PluginWithFactory)


class PluginWithoutFactory(Plugin):
    pass


class PluginWithFactory(Plugin, EnvironmentAwareFactory):
    @classmethod
    def create(cls, environment: Environment):
        return cls()


class ConfigurationTest(TestCase):
    def setUp(self):
        super().setUp()
        self._input_id = 'alfred_speech.contrib.inputs.ListInput'
        self._output_id = 'alfred_speech.contrib.outputs.NullOutput'
        self._call_signs = ['Foo', 'Bar']
        self._global_interaction_ids = [
            'alfred_speech.contrib.interactions.CallSigns']
        self._root_interaction_ids = [
            'alfred_speech.contrib.interactions.Help']
        self._locale = 'nl-NL'
        self._sut = Configuration(self._input_id, self._output_id,
                                  self._call_signs,
                                  self._global_interaction_ids,
                                  self._root_interaction_ids, self._locale)

    def testInputId(self):
        self.assertEqual(self._sut.input_id, self._input_id)

    def testOutputId(self):
        self.assertEqual(self._sut.output_id, self._output_id)

    def testCallSigns(self):
        self.assertEqual(self._sut.call_signs, self._call_signs)

    def testGlobalInteractionIds(self):
        self.assertEqual(
            self._sut.global_interaction_ids, self._global_interaction_ids)

    def testRootInteractionIds(self):
        self.assertEqual(self._sut.root_interaction_ids,
                         self._root_interaction_ids)

    def testLocale(self):
        self.assertEqual(self._sut.locale, self._locale)


class PluginTest(TestCase):
    def testId(self):
        self.assertEqual('alfred_speech.core:Plugin', Plugin().id)


class EnvironmentTest(TestCase):
    def setUp(self):
        super().setUp()
        self._input_id = 'alfred_speech.contrib.inputs:ListInput'
        self._output_id = 'alfred_speech.contrib.outputs:NullOutput'
        self._call_signs = []
        self._global_interaction_ids = []
        self._root_interaction_ids = []
        self._configuration = Configuration(
            self._input_id,
            self._output_id, self._call_signs, self._global_interaction_ids,
            self._root_interaction_ids)
        self._sut = Environment(self._configuration)

    def testConfiguration(self):
        self.assertEqual(self._sut.configuration, self._configuration)

    def testOutput(self):
        self.assertEqual(self._sut.output.id, self._output_id)

    def testPlugins(self):
        self.assertIsInstance(self._sut.plugins, PluginRepository)

    def testCurrentInteraction(self):
        self.assertIsInstance(self._sut.current_interaction, Interaction)


class ListenerTest(TestCase):
    def setUp(self):
        super().setUp()

        self._input_id = 'alfred_speech.contrib.inputs.ListInput'
        self._output_id = 'alfred_speech.contrib.outputs.ListOutput'
        self._call_signs = ['Alfred']
        self._global_interaction_ids = [
            'alfred_speech.contrib.interactions.CallSign']
        self._root_interaction_ids = [qualname(FooInteraction)]
        self._configuration = Configuration(self._input_id, self._output_id,
                                            self._call_signs,
                                            self._global_interaction_ids,
                                            self._root_interaction_ids)

        self._environment = Environment(self._configuration)

        self._input = self._environment.plugins.get(self._input_id)

        self._sut = Listener(self._environment, self._input)

    def testListenToCallSign(self):
        self._input.append('Alfred')
        self._sut.listen()
        self.assertEqual(self._environment.output, ['Yes?'])

    def testTraverseInteractions(self):
        # Use the call sign to active Alfred.
        self._input.append('Alfred')
        # Enter the top-level interaction.
        self._input.append('Foo')
        # Enter the second-level interaction twice, to cover interactions
        # going back to where they 'came' from if they do not provide new
        # interactions.
        self._input.append('Bar')
        self._input.append('Bar')
        self._sut.listen()
        self.assertEqual(self._environment.output, ['Yes?', 'Bar', 'Bar'])

    def testTraverseInteractionsWithoutCallSign(self):
        self._input.append('Foo')
        self._sut.listen()
        self.assertEqual(self._environment.output, [])


class FooInteraction(EnvironmentAwareInteraction):
    @property
    def name(self) -> str:
        return 'Foo'

    def knows(self, phrase: str):
        if self.name == phrase:
            return State()
        return None

    def enter(self, state: State):
        pass

    def get_interactions(self) -> Iterable[Interaction]:
        return [self._environment.plugins.get(
            qualname(BarInteraction))]


class BarInteraction(EnvironmentAwareInteraction):
    @property
    def name(self) -> str:
        return 'Bar'

    def knows(self, phrase: str):
        if self.name == phrase:
            return State()
        return None

    def enter(self, state: State):
        self._environment.output.say(self.name)
