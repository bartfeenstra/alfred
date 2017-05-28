from typing import Iterable

from alfred_speech.core import Input, Environment
from contracts import contract
from pocketsphinx import LiveSpeech


class SphinxInput(Input):
    def __init__(self, environment: Environment):
        super(SphinxInput, self).__init__(environment)
        self._sphinx = LiveSpeech()

    @contract
    def listen(self) -> Iterable[str]:
        try:
            for phrase in self._sphinx:
                yield str(phrase)
        except (StopIteration, RuntimeError):
            pass


class StdInput(Input):
    @contract
    def listen(self) -> Iterable[str]:
        try:
            yield input('Say something:')
        except EOFError:
            pass
