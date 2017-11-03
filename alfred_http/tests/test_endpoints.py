from typing import Optional, Dict
from unittest import TestCase

from alfred_http.endpoints import ResponseJsonSchemaEndpoint
from alfred_http.flask.app import FlaskApp
from alfred_http.json import Json


class EndpointTestCase(TestCase):
    def setUp(self):
        self._flask_app = FlaskApp()
        self._flask_app.config.update(SERVER_NAME='localhost')
        self._flask_app_context = self._flask_app.app_context()
        self._flask_app_context.push()
        self._flask_app_client = self._flask_app.test_client()
        self._app = self._flask_app.app

    def tearDown(self):
        self._flask_app_context.pop()

    def request(self, endpoint_name: str, parameters: Optional[Dict]):
        if parameters is None:
            parameters = {}
        urls = self._app.service('http', 'urls')
        url = urls.build(endpoint_name, parameters)
        http_response = self._flask_app_client.get(url)
        response_data = http_response.get_data(as_text=True)
        print(response_data)
        json_validator = self._app.service('http', 'json_validator')
        json_validator.validate(Json.from_raw(response_data))
        return http_response


class ResponseJsonSchemaEndpointTestCase(EndpointTestCase):
    def testEndpointShouldReturnSchema(self):
        endpoint_name = ResponseJsonSchemaEndpoint.NAME
        parameters = {
            'endpoint_name': endpoint_name
        }
        http_response = self.request(endpoint_name, parameters)
