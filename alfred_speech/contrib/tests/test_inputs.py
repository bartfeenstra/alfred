from unittest import mock, TestCase

from alfred_speech.contrib import inputs
import pocketsphinx


class SphinxInputTest(TestCase):
    _speech = ['Hello, world!', 'My name is Alfred.', 'How are you?']

    class LiveSpeech(pocketsphinx.LiveSpeech):
        def __init__(self):
            # Prevent the original (super) code from being run.
            pass

        def __iter__(self):
            for phrase in SphinxInputTest._speech:
                yield phrase

    @mock.patch('pocketsphinx.LiveSpeech', LiveSpeech)
    def testListen(self,):
        sut = inputs.SphinxInput()
        self.assertEqual(self.__class__._speech, list(sut.listen()))


class ListInputTest(TestCase):
    _speech = ['Hello, world!', 'My name is Alfred.', 'How are you?']

    def testListen(self):
        sut = inputs.ListInput(self.__class__._speech)
        self.assertEqual(self.__class__._speech, list(sut.listen()))


class StdInputTest(TestCase):
    _speech = ['Hello, world!', 'My name is Alfred.', 'How are you?']

    @mock.patch('builtins.input', side_effect=_speech)
    def testListen(self, m_input):
        sut = inputs.StdInput()
        self.assertEqual(self.__class__._speech, list(sut.listen()))

    @mock.patch('builtins.input', side_effect=EOFError)
    def testListenWithEOFError(self, m_input):
        sut = inputs.StdInput()
        self.assertEqual([], list(sut.listen()))

    @mock.patch('builtins.input', side_effect=KeyboardInterrupt)
    def testListenWithKeyBoardInterrupt(self, m_input):
        sut = inputs.StdInput()
        self.assertEqual([], list(sut.listen()))
