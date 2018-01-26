from typing import Dict, List, Callable
from urllib.parse import urlunsplit, urlsplit

from contracts import contract

from alfred_http import base64_encodes
from alfred_http.endpoints import EndpointUrlBuilder
from alfred_json.rewriter import Rewriter


class ExternalReferenceProxy(Rewriter):
    """
    Rewrites JSON Schemas to proxy references through
    ExternalJsonSchemaEndpoint.
    """

    _REWRITE_KEYS = ('id', '$ref', '$schema')

    @contract
    def __init__(self, base_url: Callable, urls: EndpointUrlBuilder):
        self._base_url = base_url
        self._urls = urls

    def rewrite_pointer(self, pointer):
        """
        Rewrites a JSON pointer in "id", "$ref", and "$schema" keys.
        :param pointer: Any
        :return: Any
        """
        # Rewrite URLs only.
        if not isinstance(pointer, str):
            return pointer

        # Skip pointers that have been rewritten already.
        if pointer.startswith(self._base_url()):
            return pointer

        original_parts = urlsplit(pointer)
        # Check if the schema is external and has an absolute URL.
        if original_parts[0] is not None and original_parts.netloc:
            # Rewrite the reference to point to this endpoint.
            fragment = original_parts[4]
            decoded_original_parts = original_parts[:4] + (
                None,) + original_parts[5:]
            decoded_original = urlunsplit(decoded_original_parts)
            encoded_original = base64_encodes(decoded_original)
            new_url = self._urls.build('external-schema', {
                'id': encoded_original,
            })
            new_parts = urlsplit(new_url)
            new_parts = new_parts[:4] + (fragment,) + new_parts[5:]
            new_url = urlunsplit(new_parts)
            return new_url

        return pointer

    def rewrite(self, schema):
        return self._rewrite(schema)

    def _rewrite(self, data):
        if isinstance(data, List):
            for item in data:
                # Traverse child elements.
                self._rewrite(item)
            return data
        elif isinstance(data, Dict):
            for key in data:
                if key in self._REWRITE_KEYS:
                    data[key] = self.rewrite_pointer(data[key])

                # Traverse child elements.
                else:
                    data[key] = self._rewrite(data[key])
            return data
        return data
