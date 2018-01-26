import json
import traceback
from typing import Optional, Dict, Iterable
from urllib.parse import urldefrag

from contracts import contract
from jsonschema import RefResolver
from jsonschema.validators import validator_for

from alfred import indent, format_iter
from alfred_http.endpoints import ErrorResponseType
from alfred_http.tests import HttpTestCase
from alfred_rest.endpoints import JsonPayloadType
from alfred_rest.tests.extension.extension import RestTestExtension


class RestTestCase(HttpTestCase):
    def get_extension_classes(self):
        return super().get_extension_classes() + [RestTestExtension]

    def request(self, endpoint_name: str, body: Optional[str] = None,
                parameters: Optional[Dict] = None,
                headers: Optional[Dict] = None):
        response = super().request(endpoint_name, body, parameters, headers)

        if 'Content-Type' not in response.headers or 'application/json' != \
                response.headers['Content-Type']:
            return response

        endpoint = self._app.service(
            'http', 'endpoints').get_endpoint(endpoint_name)
        response_types = [endpoint.response_type, ErrorResponseType()]
        response_types = filter(lambda rt: len(
            list(filter(lambda pt: isinstance(pt, JsonPayloadType),
                        rt.get_payload_types()))), response_types)
        if not response_types:
            raise AssertionError(
                'This request did not expect a JSON response.')

        requirements = []
        for response_type in response_types:
            try:
                schema_url = self._app.service(
                    'http', 'urls').build('schema')
                response_schema_url = '%s#/definitions/response/%s' % (
                    schema_url, response_type.name)
                response_schema = self._get_schema(response_schema_url)
                json_validator = self._app.service('json', 'validator')
                json_validator.validate(json.loads(
                    response.body.content), response_schema)
                requirements = []
                break
            except Exception:
                requirements.append(
                    indent(traceback.format_exc()))

        requirements = set(requirements)
        response_labels = format_iter(
            list(map(lambda x: '"%s" (%s)' % (x.name, type(x)),
                     response_types)))
        message = [
            'The response claims to contain JSON, but it cannot be validated against the JSON responses defined for this endpoint:\n%s\nOne of the following requirements must be met:' % response_labels]
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
    def _get_schema(self, schema_id: str) -> Dict:
        """
        Gets a JSON Schema from a URL.
        :param url:
        :return:
        :raises requests.HTTPError
        :raises json.decoder.JSONDecodeError
        """
        url, fragment = urldefrag(schema_id)
        schema = self._app.service('json', 'schemas').get_schema(url)
        if fragment:
            url, schema = RefResolver.from_schema(schema).resolve(schema_id)
            schema['id'] = url
        else:
            cls = validator_for(schema)
            cls.check_schema(schema)
        return schema

    @contract
    def assertRestErrorResponse(self, error_codes: Iterable, response):
        data = json.loads(response.body.content)
        schema_url = self._app.service('http', 'urls').build('schema')
        response_schema_url = '%s#/definitions/response/error' % (schema_url,)
        response_schema = self._get_schema(response_schema_url)
        json_validator = self._app.service('json', 'validator')
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
