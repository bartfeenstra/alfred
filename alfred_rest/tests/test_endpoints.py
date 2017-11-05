from alfred_rest.endpoints import ResponseJsonSchemaEndpoint
from alfred_rest.tests import RestTestCase


class ResponseJsonSchemaEndpointTest(RestTestCase):
    def testEndpointShouldReturnSchema(self):
        self.skipTest('Finish the HTTP and OpenAPI packages first.')
        endpoint_name = ResponseJsonSchemaEndpoint.NAME
        parameters = {
            'endpoint_name': endpoint_name
        }
        http_response = self.request(endpoint_name, parameters)
