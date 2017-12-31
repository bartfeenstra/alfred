import traceback
from typing import Optional, Dict, Iterable

import requests
from contracts import contract
from jsonschema import RefResolver
from jsonschema.validators import validator_for

from alfred import indent, format_iter
from alfred_http.tests import HttpTestCase
from alfred_rest.endpoints import JsonMessageMeta
from alfred_rest.tests.extension.extension import RestTestExtension


class RestTestCase(HttpTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [RestTestExtension]

    def request(self, endpoint_name: str, parameters: Optional[Dict] = None,
                headers: Optional[Dict] = None):
        # @todo Validate request data too. But the app under test validates requests already...
        response = super().request(endpoint_name, parameters, headers)
        if 'Content-Type' in response.headers and 'json' in response.headers[
                'Content-Type']:
            endpoint = self._app.service(
                'http', 'endpoints').get_endpoint(endpoint_name)
            response_metas = [endpoint.response_meta] + \
                self._app.service('http', 'error_response_metas').get_metas()
            response_metas = [rm for rm in response_metas if isinstance(rm, JsonMessageMeta)]
            if not response_metas:
                raise AssertionError(
                    'This request did not expect a JSON response.')
            requirements = []
            for response_meta in response_metas:
                try:
                    schema_url = self._app.service(
                        'http', 'urls').build('schema')
                    response_schema_url = '%s#/definitions/response/%s' % (
                        schema_url, response_meta.name)
                    response_schema = self._get_schema(response_schema_url)
                    json_validator = self._app.service(
                        'rest', 'json_validator')
                    json_validator.validate(response.json(), response_schema)
                    requirements = []
                    break
                except Exception:
                    requirements.append(
                        indent(traceback.format_exc()))

            requirements = set(requirements)
            response_labels = format_iter(
                list(map(lambda x: '"%s" (%s)' % (x.name, type(x)), response_metas)))
            message = ['The response claims to contain JSON, but it cannot be validated against the JSON responses defined for this endpoint:\n%s\nOne of the following requirements must be met:' % response_labels]
            if requirements:
                for requirement in requirements:
                    message.append("\n".join(
                        map(lambda line: '    %s' % line,
                            requirement.split("\n"))))
                    message.append('OR')
                message = message[:-1]
                raise AssertionError("\n".join(message))
        return response

    @contract
    def _get_schema(self, url: str) -> Dict:
        """
        Gets a JSON Schema from a URL.
        :param url:
        :return:
        :raises requests.HTTPError
        :raises json.decoder.JSONDecodeError
        """
        # @todo Replace this method with direct access to schemas through Python.
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
        return schema

    @contract
    def assertRestErrorResponse(self, error_codes: Iterable, response):
        data = response.json()
        schema_url = self._app.service('http', 'urls').build('schema')
        response_schema_url = '%s#/definitions/response/error' % (schema_url,)
        response_schema = self._get_schema(response_schema_url)
        json_validator = self._app.service('rest', 'json_validator')
        json_validator.validate(data, response_schema)
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
