from typing import Iterable

import pocketsphinx
from alfred_speech.core import Input


class SphinxInput(Input):
    def listen(self) -> Iterable[str]:
        for phrase in pocketsphinx.LiveSpeech():
            yield str(phrase)


class StdInput(Input):
    def listen(self) -> Iterable[str]:
        while True:
            try:
                yield input('Say something:')
            # Stop iteration when the input ends.
            except EOFError:
                raise StopIteration
            # Stop iteration upon user request.
            except KeyboardInterrupt:
                raise StopIteration


class ListInput(Input, list):
    def listen(self) -> Iterable[str]:
        for phrase in self:
            yield phrase
