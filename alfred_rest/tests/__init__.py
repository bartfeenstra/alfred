from typing import Optional, Dict

from alfred_http.tests import HttpTestCase
from alfred_rest.extension import RestExtension
from alfred_rest.json import Json


class RestTestCase(HttpTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [RestExtension]

    def request(self, endpoint_name: str, parameters: Optional[Dict]=None, headers: Optional[Dict]=None):
        # @todo Validate request data too.
        response = super().request(endpoint_name, parameters, headers)
        json_validator = self._app.service('rest', 'json_validator')
        json_validator.validate(Json.from_raw(response.text))
        return response
