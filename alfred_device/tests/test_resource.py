from unittest import TestCase

from alfred_device.device import DeviceRepository, DeviceNotFound, Device
from alfred_device.resource import DeviceResourceRepository, DeviceType
from alfred_json.type import OutputDataType
from alfred_rest.resource import ResourceNotFound


class DeviceResourceRepositoryTest(TestCase):
    class NoDevices(DeviceRepository):
        def get_device(self, device_id: str):
            raise DeviceNotFound(device_id)

        def get_devices(self):
            return ()

    class SomeDevices(DeviceRepository):
        def __init__(self):
            self._devices = {
                'foo': Device('foo', 'test'),
                'bar': Device('bar', 'test'),
            }

        def get_device(self, device_id: str):
            try:
                return self._devices[device_id]
            except KeyError:
                raise DeviceNotFound(device_id)

        def get_devices(self):
            return self._devices.values()

    def testGetType(self):
        devices = self.NoDevices()
        sut = DeviceResourceRepository(DeviceType(), devices)
        self.assertIsInstance(sut.get_type(), OutputDataType)

    def testGetResource(self):
        devices = self.SomeDevices()
        sut = DeviceResourceRepository(DeviceType(), devices)
        sut.get_resource('foo')

    def testGetResourceWithoutResources(self):
        devices = self.NoDevices()
        sut = DeviceResourceRepository(DeviceType(), devices)
        with self.assertRaises(ResourceNotFound):
            sut.get_resource('foo')

    def testGetResourceWithUnknownResources(self):
        devices = self.SomeDevices()
        sut = DeviceResourceRepository(DeviceType(), devices)
        with self.assertRaises(ResourceNotFound):
            sut.get_resource('baz')

    def testGetResourcesWithoutResources(self):
        devices = self.NoDevices()
        sut = DeviceResourceRepository(DeviceType(), devices)
        self.assertEquals(len(sut.get_resources()), 0)

    def testGetResourcesWithSomeResources(self):
        devices = self.SomeDevices()
        sut = DeviceResourceRepository(DeviceType(), devices)
        self.assertNotEquals(len(sut.get_resources()), 0)
