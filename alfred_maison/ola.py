from subprocess import call
from typing import Dict, Iterable

from contracts import contract


class DmxPanel:
    def __init__(self, universe=1, max_channels=512):
        self._universe = universe
        self._channels = []
        # Register the entire panel, and turn off all channels by default.
        for _ in range(max_channels):
            self._channels.append(0)
        self._send(max_channels)

    @contract
    def set(self, channel: int, value: int):
        assert channel in self._channels
        assert 0 <= value <= 255
        self._channels[channel] = value
        self._send(channel)

    @contract
    def set_multiple(self, values: Dict):
        for channel, value in values:
            self._channels[channel] = value
        self._send(max(values))

    @contract
    def get(self, channel: int) -> int:
        return self._channels[channel]

    @contract
    def get_multiple(self, channels: Iterable) -> Iterable:
        values = {}
        for channel in channels:
            values[channel] = self._channels[channel]
        return values

    @contract
    def _send(self, last_channel: int):
        send_values = self._channels[0:last_channel]
        ola_dmx_values = ','.join(map(str, send_values))
        call(['ola_set_dmx', '-u', str(self._universe), '-d', ola_dmx_values])

