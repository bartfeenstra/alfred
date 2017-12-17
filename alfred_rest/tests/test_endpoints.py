from jsonschema import validate

from alfred_http.endpoints import NotFoundError
from alfred_rest import base64_encodes, json_schema
from alfred_rest.tests import RestTestCase


class JsonSchemaEndpointTest(RestTestCase):
    def testEndpointShouldReturnSchema(self):
        content_type = 'application/schema+json'
        response = self.request('schema', headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType(content_type, response)
        actual_schema = response.json()
        validate(actual_schema, json_schema())
        expected_response_schema = {
            'anyOf': [
                {
                    '$ref': 'http://127.0.0.1:5000/about/json/schema#/definitions/response/error',
                },
                {
                    '$ref': 'http://127.0.0.1:5000/about/json/external-schema/aHR0cDovL2pzb24tc2NoZW1hLm9yZy9kcmFmdC0wNC9zY2hlbWE%3D',
                    'description': 'A JSON Schema.'
                }
            ],
        }
        self.assertIn('definitions', actual_schema)
        self.assertIn('response', actual_schema['definitions'])
        self.assertIn('schema', actual_schema['definitions']['response'])
        self.assertEquals(actual_schema['definitions']['response']
                          ['schema'], expected_response_schema)


class ExternalJsonSchemaEndpointTest(RestTestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def testEndpointShouldReturnSchema(self):
        external_schema_url = 'http://json-schema.org/draft-04/schema#'

        content_type = 'application/schema+json'
        response = self.request('external-schema', parameters={
            'id': base64_encodes(external_schema_url),
        }, headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType(content_type, response)
        actual_schema = response.json()
        expected_schema = json_schema()
        self.assertEquals(actual_schema, expected_schema)

    def testEndpointShouldHandleMissingSchema(self):
        external_schema_url = 'http://example.com/schema#'

        content_type = 'application/schema+json'
        response = self.request('external-schema', parameters={
            'id': base64_encodes(external_schema_url),
        }, headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(404, response)
        self.assertRestErrorResponse((NotFoundError.CODE,), response)
