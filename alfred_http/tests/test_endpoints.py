from typing import Optional, Dict
from unittest import TestCase

from alfred.extension import CoreExtension, ResponseJsonSchemaEndpoint
from alfred_http.flask.app import App
from alfred_http.json import Json


class EndpointTestCase(TestCase):
    def setUp(self):
        self._app = App()
        self._app.config.update(SERVER_NAME='localhost')
        self._app_context = self._app.app_context()
        self._app_context.push()
        self._app_client = self._app.test_client()

    def tearDown(self):
        self._app_context.pop()

    def request(self, endpoint_name: str, parameters: Optional[Dict]):
        core = self._app._extensions.get_extension(CoreExtension)
        if parameters is None:
            parameters = {}
        url = core.urls.build(endpoint_name, parameters)
        http_response = self._app_client.get(url)
        response_data = http_response.get_data(as_text=True)
        print(response_data)
        core.json_validator.validate(Json.from_raw(response_data))
        return http_response


class ResponseJsonSchemaEndpointTestCase(EndpointTestCase):
    def testEndpointShouldReturnSchema(self):
        endpoint_name = ResponseJsonSchemaEndpoint.NAME
        parameters = {
            'endpoint_name': endpoint_name
        }
        http_response = self.request(endpoint_name, parameters)
