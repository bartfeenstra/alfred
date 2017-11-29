import requests
from jsonschema import validate

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
        spec = response.json()
        schema = requests.get(
            'http://json-schema.org/draft-04/schema#').json()
        validate(spec, schema)
        endpoints = self._app.service('http', 'endpoints')
        endpoint = endpoints.get_endpoint('schema')
        rewriter = self._app.service('rest', 'json_reference_rewriter')
        response_schema = endpoint.response_meta.get_json_schema()
        rewriter.rewrite(response_schema)
        self.assertIn('definitions', spec)
        self.assertIn('response', spec['definitions'])
        self.assertIn('schema', spec['definitions']['response'])
        self.assertEquals(spec['definitions']['response']
                          ['schema'], response_schema.data)


class ExternalJsonSchemaEndpointTest(RestTestCase):
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
        spec = response.json()
        schema = requests.get(
            'http://json-schema.org/draft-04/schema#').json()
        validate(spec, schema)
        endpoints = self._app.service('http', 'endpoints')
        endpoint = endpoints.get_endpoint('external-schema')
        rewriter = self._app.service('rest', 'json_reference_rewriter')
        response_schema = endpoint.response_meta.get_json_schema()
        rewriter.rewrite(response_schema)
        self.assertIn('definitions', spec)
        self.assertIn('response', spec['definitions'])
        self.assertIn('schema', spec['definitions']['response'])
        self.assertEquals(spec['definitions']['response']
                          ['schema'], response_schema.data)
