import json
import urllib

import requests
from jsonschema import validate

from alfred_openapi.tests import OpenApiTestCase


class OpenApiEndpointTest(OpenApiTestCase):
    def testEndpoint(self):
        spec_data = self.request('openapi', headers={
            'Accept': 'application/json',
        }).get_data(as_text=True)
        spec = json.loads(spec_data)
        schema = requests.get(
            'https://raw.githubusercontent.com/OAI/OpenAPI-Specification/master/schemas/v2.0/schema.json').json()
        validate(spec, schema)
