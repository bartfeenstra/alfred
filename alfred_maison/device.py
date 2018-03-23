from contracts import contract
from py_irsend.irsend import send_once

from alfred.app import App
from alfred_device.device import Rgb24Colorable, Powerable, Device, \
    Illuminative, Rgb24Color
from alfred_device.resource import PowerableType, DeviceType, \
    Rgb24ColorableType, IlluminativeType
from alfred_json.type import InputDataType, UpdateInputDataType


class OlaType(DeviceType, PowerableType, Rgb24ColorableType, IlluminativeType,
              InputDataType, UpdateInputDataType):
    def __init__(self):
        DeviceType.__init__(self, 'ola')
        PowerableType.__init__(self)
        Rgb24ColorableType.__init__(self)
        IlluminativeType.__init__(self)
        InputDataType.__init__(self)

    def get_json_schema(self):
        schema = DeviceType.get_json_schema(self)
        schema.update(PowerableType.get_json_schema(self))
        schema.update(Rgb24ColorableType.get_json_schema(self))
        schema.update(IlluminativeType.get_json_schema(self))
        return schema

    def from_json(self, json_data):
        # We cannot really replace the entire resource, because it depends on
        #  internal, real-world factors, such as the DMX panel configuration.
        #  Therefore we load the original resource and simply apply updates.
        device_id = json_data['id']
        ola = App.current.service('device', 'devices').get_device(device_id)
        assert isinstance(ola, Ola)
        return self.update_from_json(json_data, ola)

    def update_from_json(self, json_data, instance):
        assert isinstance(instance, Ola)
        instance = DeviceType.update_from_json(self, json_data, instance)
        instance = PowerableType.update_from_json(self, json_data, instance)
        instance = Rgb24ColorableType.update_from_json(
            self, json_data, instance)
        instance = IlluminativeType.update_from_json(self, json_data, instance)
        return instance

    def to_json(self, data):
        json_data = {}
        json_data.update(DeviceType.to_json(self, data))
        json_data.update(PowerableType.to_json(self, data))
        json_data.update(Rgb24ColorableType.to_json(self, data))
        json_data.update(IlluminativeType.to_json(self, data))
        return json_data


class Ola(Device, Powerable, Rgb24Colorable, Illuminative):
    def __init__(self, device_id, red_channel: int, green_channel: int,
                 blue_channel: int, luminosity_channel: int, label=None):
        Device.__init__(self, device_id, 'ola', label)
        Powerable.__init__(self)
        Rgb24Colorable.__init__(self)
        Illuminative.__init__(self)
        self._dmx = App.current.service('maison', 'dmx_panel')
        self._red_channel = red_channel
        self._green_channel = green_channel
        self._blue_channel = blue_channel
        self._luminosity_channel = luminosity_channel

    @property
    def powered(self):
        return self._powered

    @powered.setter
    def powered(self, powered):
        self._powered = powered
        self.luminosity = self._luminosity

    @property
    def luminosity(self):
        return self._luminosity

    @luminosity.setter
    def luminosity(self, luminosity):
        assert 0 <= luminosity <= 1.0
        self._luminosity = luminosity
        if not self.powered:
            luminosity = 0
        self._dmx.set(self._luminosity_channel, round(luminosity * 255))

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


class TvType(DeviceType, PowerableType, InputDataType, UpdateInputDataType):
    def __init__(self):
        DeviceType.__init__(self, 'tv')
        PowerableType.__init__(self)
        InputDataType.__init__(self)

    def get_json_schema(self):
        schema = DeviceType.get_json_schema(self)
        schema.update(PowerableType.get_json_schema(self))
        return schema

    def from_json(self, json_data):
        # We cannot really replace the entire resource, because it depends on
        #  internal, real-world factors. Therefore we load the original
        #  resource and simply apply updates.
        device_id = json_data['id']
        ola = App.current.service('device', 'devices').get_device(device_id)
        assert isinstance(ola, Ola)
        return self.update_from_json(json_data, ola)

    def update_from_json(self, json_data, instance):
        assert isinstance(instance, Ola)
        instance = DeviceType.update_from_json(self, json_data, instance)
        instance = PowerableType.update_from_json(self, json_data, instance)
        return instance

    def to_json(self, data):
        json_data = {}
        json_data.update(DeviceType.to_json(self, data))
        json_data.update(PowerableType.to_json(self, data))
        return json_data


class Tv(Powerable, Device):
    def __init__(self, remote, label=None):
        Device.__init__(self, 'tv', 'tv', label)
        Powerable.__init__(self)
        self._remote = remote

    @property
    def powered(self):
        return self._powered

    @powered.setter
    def powered(self, powered):
        self._powered = powered
        # @todo Find the discrete "power off" key.
        send_once(self._remote, 'KEY_POWER')
