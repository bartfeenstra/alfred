import json
import urllib

from jsonschema import validate

from alfred_openapi.tests import OpenApiTestCase


class OpenApiEndpointTest(OpenApiTestCase):
    def testEndpoint(self):
        spec_data = self.request('openapi').get_data(as_text=True)
        spec = json.loads(spec_data)
        schema_data = urllib.request.urlopen(
            'https://raw.githubusercontent.com/OAI/OpenAPI-Specification/master/schemas/v2.0/schema.json').read().decode(
            'utf-8')
        schema = json.loads(schema_data)
        validate(spec, schema)
