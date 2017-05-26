import os
import subprocess

import tempfile

from alfred_speech.core import Mouth
from contracts import contract


class Pico2WaveMouth(Mouth):
    @contract
    def say(self, phrase: str):
        path = self._create_file(phrase)
        self._play_file(path)
        self._remove_file(path)

    @contract
    def _create_file(self, phrase: str) -> str:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name

        cmd = ['pico2wave', '--wave', path, phrase]
        subprocess.call(cmd)
        return path

    @contract
    def _remove_file(self, path: str):
        os.remove(path)

    @contract()
    def _play_file(self, path: str):
        cmd = ['aplay', path]
        subprocess.call(cmd)
