from unittest import mock, TestCase
from unittest.mock import call

from alfred_speech.contrib import outputs


class ListOutputTest(TestCase):
    _speech = ['Hello, world!', 'My name is Alfred.', 'How are you?']

    def testSay(self):
        sut = outputs.ListOutput()
        for phrase in self.__class__._speech:
            sut.say(phrase)
        self.assertEqual(self.__class__._speech, list(sut))


class StdOutputTest(TestCase):
    _speech = ['Hello, world!', 'My name is Alfred.', 'How are you?']

    @mock.patch('builtins.print')
    def testListen(self, m_print):
        sut = outputs.StdOutput()
        expected_calls = list(map(lambda phrase: call(phrase),
                                  self.__class__._speech))
        for phrase in self.__class__._speech:
            sut.say(phrase)
        m_print.assert_has_calls(expected_calls)


class NullOutputTest(TestCase):
    _speech = ['Hello, world!', 'My name is Alfred.', 'How are you?']

    def testListen(self):
        sut = outputs.NullOutput()
        for phrase in self.__class__._speech:
            sut.say(phrase)
