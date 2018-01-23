from alfred_device.extension import DeviceExtension
from alfred_rest.tests import RestTestCase


class DeviceTestCase(RestTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [DeviceExtension]
