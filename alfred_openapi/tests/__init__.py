from alfred_http.tests import HttpTestCase
from alfred_openapi.extension import OpenApiExtension


class OpenApiTestCase(HttpTestCase):
    @property
    def extension_classes(self):
        return [OpenApiExtension]
