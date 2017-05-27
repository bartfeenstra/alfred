import subprocess

import tempfile

from alfred_speech.core import Output
from contracts import contract


class Pico2WaveOutput(Output):
    @contract
    def say(self, phrase: str):
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            subprocess.call(['pico2wave', '--wave', f.name, phrase])
            subprocess.call(['aplay', f.name])


class StdOutput(Output):
    @contract
    def say(self, phrase: str):
        print(phrase)
