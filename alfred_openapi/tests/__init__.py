from alfred_http.tests import HttpTestCase
from alfred_openapi.extension import OpenApiExtension


class OpenApiTestCase(HttpTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [OpenApiExtension]
