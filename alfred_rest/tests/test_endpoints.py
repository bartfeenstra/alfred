import requests
from jsonschema import validate

from alfred_rest.tests import RestTestCase


class JsonSchemaEndpointTest(RestTestCase):
    def testEndpointShouldReturnSchema(self):
        content_type = 'application/schema+json'
        response = self.request('schema', headers={
            'Accept': content_type,
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType(content_type, response)
        spec = response.json()
        schema = requests.get(
            'http://json-schema.org/draft-04/schema#').json()
        validate(spec, schema)
        print(spec)
        endpoints = self._app.service('http', 'endpoints')
        endpoint = endpoints.get_endpoint('schema')
        response_schema = endpoint.response_meta.get_json_schema().raw
        self.assertEquals(spec['definitions/response/schema'], response_schema)
