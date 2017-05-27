from typing import Iterable

from alfred_speech.core import Ear
from contracts import contract
from pocketsphinx import LiveSpeech


class SphinxEar(Ear):
    def __init__(self):
        self._sphinx = LiveSpeech()

    @contract
    def listen(self) -> Iterable[str]:
        try:
            for phrase in self._sphinx:
                yield str(phrase)
        except (StopIteration, RuntimeError):
            pass


class StdInEar(Ear):
    @contract
    def listen(self) -> Iterable[str]:
        try:
            yield input('Say something:')
        except EOFError:
            pass
