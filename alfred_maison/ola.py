import subprocess
from typing import Dict, Iterable

from contracts import contract


class DmxPanel:
    def __init__(self, universe=1, max_channels=512):
        self._universe = universe
        self._channels = []
        # Register the entire panel.
        for _ in range(max_channels):
            self._channels.append(0)

    @contract
    def set(self, channel: int, value: int):
        self.set_multiple({
            channel: value,
        })

    @contract
    def set_multiple(self, values: Dict):
        for channel, value in values.items():
            self._assert_channel(channel)
            self._assert_value(value)
            self._channels[channel - 1] = value
        self._send()

    @contract
    def get(self, channel: int) -> int:
        self._assert_channel(channel)
        return self._channels[channel - 1]

    @contract
    def get_multiple(self, channels: Iterable) -> Iterable:
        values = {}
        for channel in channels:
            self._assert_channel(channel)
            values[channel - 1] = self.get(channel)
        return values

    @contract
    def _assert_channel(self, channel: int):
        if channel < 1 or channel > len(self._channels):
            raise ValueError('Channel %d does not exist on this DMX panel (0-%d).' % (channel, len(self._channels) - 1))

    @contract
    def _assert_value(self, value: int):
        if value < 0 or value > 255:
            raise ValueError('Values must be 0-255, but %d was given.' % value)

    def _send(self):
        subprocess.call(
            ['ola_set_dmx', '-u', str(self._universe), '-d', ','.join(map(str, self._channels))])
