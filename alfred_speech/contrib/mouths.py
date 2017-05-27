import subprocess

import tempfile

from alfred_speech.core import Mouth
from contracts import contract


class Pico2WaveMouth(Mouth):
    @contract
    def say(self, phrase: str):
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            subprocess.call(['pico2wave', '--wave', f.name, phrase])
            subprocess.call(['aplay', f.name])


class StdOutMouth(Mouth):
    @contract
    def say(self, phrase: str):
        print(phrase)
