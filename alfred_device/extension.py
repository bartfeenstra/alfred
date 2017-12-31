from alfred.app import Extension
from alfred_device.device import NestedDeviceRepository
from alfred_device.resource import DeviceResourceRepository
from alfred_rest.extension import RestExtension


class DeviceExtension(Extension):
    @staticmethod
    def name():
        return 'device'

    @staticmethod
    def dependencies():
        return [RestExtension]

    @Extension.service()
    def _devices(self):
        devices = NestedDeviceRepository()
        for tagged_device in self._app.services(tag='devices'):
            devices.add_devices(tagged_device)
        return devices

    @Extension.service(tags=('resources',))
    def _device_resources(self):
        return DeviceResourceRepository(self._app.service('device', 'devices'))
