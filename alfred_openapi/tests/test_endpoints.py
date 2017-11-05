from alfred_http.tests import HttpTestCase


class OpenApiEndpointTest(HttpTestCase):
    def testEndpoint(self):
        self.skipTest('Finish the HTTP package first')
        http_response = self.request('openapi')
