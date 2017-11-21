import requests
from jsonschema import validate

from alfred_openapi.tests import OpenApiTestCase


class OpenApiEndpointTest(OpenApiTestCase):
    def testEndpointWithJson(self):
        response = self.request('openapi', headers={
            'Accept': 'application/json',
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType('application/json', response)
        spec = response.json()
        schema = requests.get(
            'https://raw.githubusercontent.com/OAI/OpenAPI-Specification/master/schemas/v2.0/schema.json').json()
        validate(spec, schema)

    def testEndpointWithHtml(self):
        response = self.request('openapi', headers={
            'Accept': 'text/html',
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType('text/html', response)
