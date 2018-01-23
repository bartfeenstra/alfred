from alfred_device.tests import DeviceTestCase
from alfred_maison.extension import MaisonExtension


class MaisonTestCase(DeviceTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [MaisonExtension]
