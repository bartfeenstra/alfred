import requests
from jsonschema import validate

from alfred.tests import data_provider
from alfred_http.tests import provide_5xx_codes
from alfred_rest import base64_encodes
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
        json_schema = requests.get(
            'http://json-schema.org/draft-04/schema#').json()
        validate(actual_schema, json_schema)
        expected_response_schema = {
            'oneOf': [
                {
                    'type': 'object',
                    'properties': {
                        'errors': {
                            'type': 'array',
                            'items': {
                                '$ref': '#/definitions/data/error',
                            },
                        },
                    },
                    'required': ['errors'],
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


class ExternalJsonSchemaReferenceProxyEndpointTest(RestTestCase):
    def testEndpointShouldReturnSchema(self):
        urls = self._app.service('http', 'urls')
        external_schema_url = urls.build('schema')

        content_type = 'application/schema+json'
        response = self.request('external-schema', parameters={
            'id': base64_encodes(external_schema_url),
        }, headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType(content_type, response)
        actual_schema = response.json()
        json_schema = requests.get(
            'http://json-schema.org/draft-04/schema#').json()
        validate(actual_schema, json_schema)
        expected_response_schema = {
            'oneOf': [
                {
                    'type': 'object',
                    'properties': {
                        'errors': {
                            'type': 'array',
                            'items': {
                                '$ref': '#/definitions/data/error',
                            },
                        },
                    },
                    'required': ['errors'],
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

    @data_provider(provide_5xx_codes)
    def testWithUpstream5xxResponse(self, upstream_status_code):
        urls = self._app.service('http', 'urls')
        external_schema_url = urls.build('rest-test-programmed', {
            'code': upstream_status_code
        })

        content_type = 'application/schema+json'
        response = self.request('external-schema', parameters={
            'id': base64_encodes(external_schema_url),
        }, headers={
            'Accept': content_type,
        })
