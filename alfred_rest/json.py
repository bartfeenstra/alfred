import base64
import json
from typing import Optional, Dict, List, Any
from urllib.parse import urlunsplit, urlsplit

import requests
from contracts import contract
from jsonschema import RefResolver, validate

from alfred_http.endpoints import EndpointUrlBuilder


class Json:
    def __init__(self, data):
        # Try dumping the data to ensure it is valid.
        json.dumps(data)
        self._data = data

    @classmethod
    def from_raw(cls, raw: str) -> 'Json':
        return cls(json.loads(raw))

    @classmethod
    def from_data(cls, data) -> 'Json':
        return cls(data)

    @property
    def raw(self) -> str:
        return json.dumps(self.data)

    @property
    def data(self):
        return self._data


@contract
def get_schema(url: str) -> Json:
    """
    Gets a JSON Schema from a URL.
    :param url:
    :return:
    :raises requests.HTTPError
    """
    response = requests.get(url, headers={
        'Accept': 'application/schema+json; q=1, application/json; q=0.9, */*',
    })
    response.raise_for_status()
    return Json.from_raw(response.text)


class Validator:
    def validate(self, subject: Json, schema: Optional[Json] = None):
        reference_resolver = RefResolver(
            'http://localhost', 'http://localhost')
        data = subject.data
        if schema is None:
            message = 'The JSON must be an object with a "schema" key.'
            if not isinstance(data, dict):
                raise ValueError('The JSON is not an object: %s' % message)
            if '$schema' not in data:
                raise KeyError('No "$schema" key found: %s' % message)
            _, schema = reference_resolver.resolve(data['$schema'])
        else:
            schema = schema.data
        assert schema is not None
        validate(data, schema)


class Rewriter:
    """
    Rewrites JSON Schemas to proxy references through
    ExternalJsonSchemaEndpoint.
    """

    _REWRITE_KEYS = ('$ref', '$schema')

    @contract
    def __init__(self, base_url: str, urls: EndpointUrlBuilder):
        self._base_url = base_url
        self._urls = urls

    def rewrite_pointer(self, pointer: Any) -> Any:
        """
        Rewrites a JSON pointer in "id", "$ref", and "$schema" keys.
        :param pointer: Any
        :return: Any
        """
        # Rewrite URLs only.
        if not isinstance(pointer, str):
            return pointer

        # Skip pointers that have been rewritten already.
        if pointer.startswith(self._base_url):
            return pointer

        original_parts = urlsplit(pointer)
        # Check if the schema is external and has an absolute URL.
        # @todo MAKE SURE THEY DO NOT ALREADY POINT TO ALFRED. CAN WE MATCH ON BASE URL? DO WE EVEN *KNOW* THE BASE URL?
        if original_parts[0] is not None and original_parts.netloc:
            # Rewrite the reference to point to this endpoint.
            fragment = original_parts[4]
            decoded_original_parts = original_parts[:4] + (
                None,) + original_parts[5:]
            decoded_original = urlunsplit(decoded_original_parts)
            encoded_original = base64.b64encode(
                bytes(decoded_original, 'utf-8')).decode('utf-8')
            new_url = self._urls.build('external-schema', {
                'id': encoded_original,
            })
            new_parts = urlsplit(new_url)
            new_parts = new_parts[:4] + (fragment,) + new_parts[5:]
            new_url = urlunsplit(new_parts)
            return new_url

    @contract
    def rewrite(self, schema: Json):
        """
        Rewrites a JSON Schema's pointers.
        :param schema:
        :return:
        """
        self._rewrite(schema.data)
        if 'id' in schema.data:
            schema.data['id'] = self.rewrite_pointer(schema.data['id'])

    def _rewrite(self, schema):
        if isinstance(schema, List):
            for item in schema:
                # Traverse child elements.
                self._rewrite(item)
        elif isinstance(schema, Dict):
            for key in schema:
                if key in self._REWRITE_KEYS:
                    schema[key] = self.rewrite_pointer(schema[key])

                # Traverse child elements.
                else:
                    self._rewrite(schema[key])
