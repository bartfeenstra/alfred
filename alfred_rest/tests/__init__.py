from typing import Optional, Dict

from alfred_http.tests import HttpTestCase
from alfred_rest.json import Json
from alfred_rest.tests.extension import RestTestExtension


class RestTestCase(HttpTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [RestTestExtension]

    def request(self, endpoint_name: str, parameters: Optional[Dict]=None, headers: Optional[Dict]=None):
        # @todo Validate request data too.
        response = super().request(endpoint_name, parameters, headers)
        if 'Content-Type' in response.headers and 'json' in response.headers['Content-Type']:
            json_validator = self._app.service('rest', 'json_validator')
            json_validator.validate(Json.from_data(response.json()))
        return response
