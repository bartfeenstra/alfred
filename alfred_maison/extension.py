from alfred.app import Extension, App
from alfred_device.device import StaticDeviceRepository
from alfred_device.extension import DeviceExtension
from alfred_device.resource import DeviceResourceRepository
from alfred_maison.device import Ola, OlaType
from alfred_maison.ola import DmxPanel
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
    def _ola_devices(self):
        devices = StaticDeviceRepository()
        devices.add_device(Ola('stage_1', 1, 2, 3, 4, label='TV'))
        devices.add_device(Ola('stage_2', 5, 6, 7, 8, label='Window'))
        devices.add_device(Ola('stage_3', 9, 10, 11, 12, label='Couch'))
        devices.add_device(Ola('stage_4', 13, 14, 15, 16, label='Kitchen'))
        return devices

    @Extension.service(tags=('device_resources',))
    def _ola_device_resources(self):
        return DeviceResourceRepository(OlaType(), App.current.service('maison', 'ola_devices'))

    @Extension.service()
    def _dmx_panel(self):
        return DmxPanel(1, 16)
