from subprocess import call
from typing import Dict

from contracts import contract

from alfred_device.device import Rgb24Colorable, Powerable, Device
from alfred_device.resource import PowerableType, DeviceType, \
    Rgb24ColorableType
from alfred_json.type import InputDataType, UpdateInputDataType

_dmx_values = {
    'color': '#abcdef',
    'luminosity': 0,
}


@contract
def dmx_get_values() -> Dict:
    global _dmx_values
    return _dmx_values


@contract
def dmx_set_values(color: str, luminosity: int) -> Dict:
    # This assumes:
    # - 4 identical lights.
    # - 7 channels per light (R, G, B, *, *, *, luminosity).
    # - Universe 1.
    # - The first light's address is 0.
    # - All lights occupy a continuous range of addresses.
    global _dmx_values
    _dmx_values = {
        'color': color,
        'luminosity': luminosity,
    }
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    ola_dmx_values = ','.join(
        ['%s,%s,%s,0,0,0,%s' % (red, green, blue, luminosity)] * 4)
    call(['ola_set_dmx', '-u', '1', '-d', ola_dmx_values])
    return _dmx_values


# Reset the lights.
# @todo Does this execute every single time the module is included?
# dmx_set_values(_dmx_values['color'], _dmx_values['luminosity'])


class OpenDmxLightType(DeviceType, PowerableType, Rgb24ColorableType,
                       UpdateInputDataType):
    def __init__(self):
        DeviceType.__init__(self, 'open_dmx_light')
        PowerableType.__init__(self)
        Rgb24ColorableType.__init__(self)
        InputDataType.__init__(self)

    def get_json_schema(self):
        return DeviceType.get_json_schema(
            self) + PowerableType.get_json_schema(
            self) + Rgb24ColorableType.get_json_schema(self)

    def update_from_json(self, json_data, instance):
        assert isinstance(instance, OpenDmxLight)
        DeviceType.update_from_json(self, json_data, instance)
        PowerableType.update_from_json(self, json_data, instance)
        Rgb24ColorableType.update_from_json(self, json_data, instance)

    def to_json(self, data):
        json_data = {}
        json_data.update(DeviceType.to_json(self, data))
        json_data.update(PowerableType.to_json(self, data))
        json_data.update(Rgb24ColorableType.to_json(self, data))
        return json_data


class OpenDmxLight(Device, Powerable, Rgb24Colorable):
    def __init__(self, device_id):
        Device.__init__(self, device_id, 'open_dmx_light')
        Powerable.__init__(self)
        Rgb24Colorable.__init__(self)
