import subprocess

import tempfile
from alfred_speech.core import Output, EnvironmentAwareFactory, Environment


class EnvironmentAwareOutput(Output, EnvironmentAwareFactory):
    def __init__(self, environment: Environment):
        self._environment = environment

    @classmethod
    def create(cls, environment: Environment):
        return cls(environment)


class Pico2WaveOutput(EnvironmentAwareOutput):
    def say(self, phrase: str):
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            subprocess.call(['pico2wave', '--wave', f.name, '-l',
                             self._environment.configuration.locale, phrase])
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
