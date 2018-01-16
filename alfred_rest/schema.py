from typing import Dict

from contracts import contract

from alfred.app import App
from alfred_http.endpoints import ErrorResponseType
from alfred_rest.endpoints import JsonRequestPayloadType, \
    JsonResponsePayloadType, JsonPayloadType


class AlfredJsonSchema:
    def __init__(self):
        self._endpoints = None
        self._urls = App.current.service('http', 'urls')
        self._rewriter = App.current.service('json', 'schema_rewriter')
        self._error_response_type = None

    @contract
    def get(self) -> Dict:
        if not self._endpoints:
            self._endpoints = App.current.service('http', 'endpoints')
        if not self._error_response_type:
            self._error_response_type = ErrorResponseType()
        schema = {
            'id': self._urls.build('schema'),
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'description': 'The Alfred JSON Schema. Any data matches subschemas under #/definitions only.',
            # Prevent most values from validating against the top-level schema.
            'enum': [None],
            'definitions': {},
        }

        for endpoint in self._endpoints.get_endpoints():
            request_type = endpoint.request_type
            for request_payload_type in request_type.get_payload_types():
                if isinstance(request_payload_type, JsonRequestPayloadType):
                    schema['definitions'].setdefault('request', {})
                    schema['definitions']['request'].setdefault(
                        request_type.name,
                        request_payload_type.data_type.get_json_schema())

            response_type = endpoint.response_type
            for response_payload_type in response_type.get_payload_types():
                if isinstance(response_payload_type, JsonResponsePayloadType):
                    schema['definitions'].setdefault('response', {})
                    schema['definitions']['response'].setdefault(
                        response_type.name,
                        response_payload_type.data_type.get_json_schema())

        for error_response_payload_type in self._error_response_type.get_payload_types():
            if isinstance(error_response_payload_type,
                          JsonResponsePayloadType):
                schema['definitions'].setdefault('response', {})
                schema['definitions']['response'].setdefault(
                    self._error_response_type.name,
                    error_response_payload_type.data_type.get_json_schema() if isinstance(
                        error_response_payload_type, JsonPayloadType) else {})

        schema = self._rewriter.rewrite(schema)

        return schema
