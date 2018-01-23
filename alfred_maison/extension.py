from alfred.app import Extension, App
from alfred_device.device import StaticDeviceRepository
from alfred_device.extension import DeviceExtension
from alfred_device.resource import DeviceResourceRepository
from alfred_maison.device import OpenDmxLight, OpenDmxLightType
from alfred_openapi.extension import OpenApiExtension
from alfred_rest.extension import RestExtension


class MaisonExtension(Extension):
    @staticmethod
    def name():
        return 'maison'

    @staticmethod
    def dependencies():
        return [RestExtension, DeviceExtension, OpenApiExtension]

    @Extension.service(tags=('devices',))
    def _open_dmx_light_devices(self):
        devices = StaticDeviceRepository()
        devices.add_device(OpenDmxLight('stage_1'))
        devices.add_device(OpenDmxLight('stage_2'))
        devices.add_device(OpenDmxLight('stage_3'))
        devices.add_device(OpenDmxLight('stage_4'))
        return devices

    @Extension.service(tags=('device_resources',))
    def _open_dmx_light_device_resources(self):
        return DeviceResourceRepository(OpenDmxLightType(), App.current.service('maison', 'open_dmx_light_devices'))
