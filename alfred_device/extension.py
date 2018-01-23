from alfred.app import Extension, App
from alfred_device.device import NestedDeviceRepository
from alfred_device.resource import NestedDeviceResourceRepository
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
        for tagged_device in App.current.services(tag='devices'):
            devices.add_devices(tagged_device)
        return devices

    @Extension.service(tags=('resources',))
    def _device_resources(self):
        resources = NestedDeviceResourceRepository()
        for tagged_resources in App.current.services(tag='device_resources'):
            resources.add_resources(tagged_resources)
        return resources
