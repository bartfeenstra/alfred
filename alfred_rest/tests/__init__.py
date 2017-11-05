from typing import Optional, Dict

from alfred_http.tests import HttpTestCase
from alfred_rest.json import Json


class RestTestCase(HttpTestCase):
    def request(self, endpoint_name: str, parameters: Optional[Dict]=None):
        http_response = super().request(endpoint_name, parameters)
        response_data = http_response.get_data(as_text=True)
        print(response_data)
        json_validator = self._app.service('http', 'json_validator')
        json_validator.validate(Json.from_raw(response_data))
        return http_response
