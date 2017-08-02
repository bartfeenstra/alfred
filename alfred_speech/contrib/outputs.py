import subprocess

import tempfile
from alfred_speech.core import Output


class Pico2WaveOutput(Output):
    def say(self, phrase: str):
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            subprocess.call(['pico2wave', '--wave', f.name, phrase])
            subprocess.call(['aplay', f.name])


class StdOutput(Output):
    def say(self, phrase: str):
        print(phrase)


class NullOutput(Output):
    def say(self, phrase: str):
        pass


class ListOutput(Output, list):
    def say(self, phrase: str):
        self.append(phrase)
