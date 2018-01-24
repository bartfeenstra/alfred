from alfred.tests import AppTestCase
from alfred_json.extension import JsonExtension


class JsonTestCase(AppTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [JsonExtension]
