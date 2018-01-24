from contracts import contract

from alfred.app import App
from alfred_device.device import Rgb24Colorable, Powerable, Device, \
    Illuminative, Rgb24Color
from alfred_device.resource import PowerableType, DeviceType, \
    Rgb24ColorableType, IlluminativeType
from alfred_json.type import InputDataType, UpdateInputDataType


class OlaType(DeviceType, PowerableType, Rgb24ColorableType, IlluminativeType,
              UpdateInputDataType):
    def __init__(self):
        DeviceType.__init__(self, 'ola')
        PowerableType.__init__(self)
        Rgb24ColorableType.__init__(self)
        IlluminativeType.__init__(self)
        InputDataType.__init__(self)

    def get_json_schema(self):
        return DeviceType.get_json_schema(
            self) + PowerableType.get_json_schema(
            self) + Rgb24ColorableType.get_json_schema(
            self) + IlluminativeType.get_json_schema(self)

    def update_from_json(self, json_data, instance):
        assert isinstance(instance, Ola)
        DeviceType.update_from_json(self, json_data, instance)
        PowerableType.update_from_json(self, json_data, instance)
        Rgb24ColorableType.update_from_json(self, json_data, instance)
        IlluminativeType.update_from_json(self, json_data, instance)

    def to_json(self, data):
        json_data = {}
        json_data.update(DeviceType.to_json(self, data))
        json_data.update(PowerableType.to_json(self, data))
        json_data.update(Rgb24ColorableType.to_json(self, data))
        json_data.update(IlluminativeType.to_json(self, data))
        return json_data


class Ola(Device, Powerable, Rgb24Colorable, Illuminative):
    def __init__(self, device_id, red_channel: int, green_slot: int,
                 blue_slot: int, luminosity_slot: int):
        Device.__init__(self, device_id, 'ola')
        Powerable.__init__(self)
        Rgb24Colorable.__init__(self)
        Illuminative.__init__(self)
        self._dmx = App.current.service('maison', 'dmx_panel')
        self._red_channel = red_channel
        self._green_channel = green_slot
        self._blue_channel = blue_slot
        self._luminosity_slot = luminosity_slot

    @property
    def powered(self):
        return self.luminosity != 0.0

    @powered.setter
    def powered(self, powered):
        self.luminosity = 1.0 if powered else 0.0

    @property
    def luminosity(self):
        return self._dmx.get(self._luminosity_slot) / 255 * 100

    @luminosity.setter
    def luminosity(self, luminosity):
        self._dmx.set(self._luminosity_slot, round(luminosity / 100 * 255))

    @property
    def color(self):
        return Rgb24Color(*self._dmx.get_multiple(
            (self._red_channel, self._green_channel,
             self._blue_channel)).values())

    @color.setter
    @contract
    def color(self, color: Rgb24Color):
        self._dmx.set_multiple({
            self._red_channel: color.red,
            self._green_channel: color.green,
            self._blue_channel: color.blue,
        })
