from alfred_openapi.tests import OpenApiTestCase


class OpenApiEndpointTest(OpenApiTestCase):
    def testEndpoint(self):
        self.request('openapi')
