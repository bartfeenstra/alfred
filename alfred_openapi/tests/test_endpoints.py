import json

from jsonschema import validate

from alfred_openapi import openapi_schema
from alfred_openapi.tests import OpenApiTestCase


class OpenApiEndpointTest(OpenApiTestCase):
    def testEndpointWithJson(self):
        response = self.request('openapi', headers={
            'Accept': 'application/json',
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType('application/json', response)
        spec = json.loads(response.body.content)
        schema = openapi_schema()
        validate(spec, schema)

    def testEndpointWithHtml(self):
        response = self.request('openapi', headers={
            'Accept': 'text/html',
        })
        self.assertResponseStatus(200, response)
        self.assertResponseContentType('text/html', response)
