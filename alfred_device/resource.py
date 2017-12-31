from alfred_device.device import DeviceRepository, DeviceNotFound
from alfred_rest.resource import ResourceRepository, ResourceType, \
    ResourceNotFound


class DeviceType(ResourceType):
    def __init__(self):
        super().__init__({}, 'device')


class DeviceResourceRepository(ResourceRepository):
    def __init__(self, devices: DeviceRepository):
        self._devices = devices
        self._type = DeviceType()

    def get_type(self):
        return self._type

    def get_resource(self, resource_id):
        try:
            return self._devices.get_device(resource_id)
        except DeviceNotFound:
            raise ResourceNotFound(resource_id)

    def get_resources(self):
        return self._devices.get_devices()
