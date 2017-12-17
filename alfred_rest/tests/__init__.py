from typing import Optional, Dict, Iterable

import requests
from contracts import contract
from jsonschema import RefResolver
from jsonschema.validators import validator_for

from alfred_http.tests import HttpTestCase
from alfred_rest.extension import RestExtension
from alfred_rest.json import Json


class RestTestCase(HttpTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [RestExtension]

    def request(self, endpoint_name: str, parameters: Optional[Dict] = None,
                headers: Optional[Dict] = None):
        # @todo Validate request data too.
        response = super().request(endpoint_name, parameters, headers)
        if 'Content-Type' in response.headers and 'json' in response.headers[
                'Content-Type']:
            endpoint = self._app.service(
                'http', 'endpoints').get_endpoint(endpoint_name)
            schema_url = self._app.service('http', 'urls').build('schema')
            response_schema_url = '%s#/definitions/response/%s' % (
                schema_url, endpoint.response_meta.name)
            response_schema = self._get_schema(response_schema_url)
            json_validator = self._app.service('rest', 'json_validator')
            json_validator.validate(Json.from_data(
                response.json()), response_schema)
        return response

    @contract
    def _get_schema(self, url: str) -> Json:
        """
        Gets a JSON Schema from a URL.
        :param url:
        :return:
        :raises requests.HTTPError
        :raises json.decoder.JSONDecodeError
        """
        # @todo Replace this method with direct access to schemas through Python.
        # @todo Will requiring HTTPS be enough for security?
        response = requests.get(url, headers={
            'Accept': 'application/schema+json; q=1, application/json; q=0.9, text/json; q=0.8, text/x-json; q=0.7, */*',
        })
        response.raise_for_status()
        schema = response.json()
        if '#' in url:
            url, schema = RefResolver.from_schema(schema).resolve(url)
            schema['id'] = url
        else:
            cls = validator_for(schema)
            cls.check_schema(schema)
        return Json.from_data(schema)

    @contract
    def assertRestErrorResponse(self, error_codes: Iterable, response):
        data = response.json()
        schema_url = self._app.service('http', 'urls').build('schema')
        response_schema_url = '%s#/definitions/response/error' % (schema_url,)
        response_schema = self._get_schema(response_schema_url)
        json_validator = self._app.service('rest', 'json_validator')
        json_validator.validate(Json.from_data(
            data), response_schema)
        for error_code in error_codes:
            self._assertRestErrorResponseCode(error_code, data)

    @contract
    def _assertRestErrorResponseCode(self, error_code: str, data: Dict):
        for error in data['errors']:
            if error_code == error['code']:
                return
        self.fail(
            'The error response does not contain any errors with the code "%s".' % (
                error_code,))
