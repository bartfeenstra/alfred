import abc
import json
from copy import copy
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlunsplit, urlsplit

import requests
from contracts import contract, ContractsMeta, with_metaclass
from jsonschema import RefResolver, validate

from alfred_http.endpoints import EndpointUrlBuilder
from alfred_rest import base64_encodes


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


class DataType(dict):
    @contract
    def __init__(self, schema: Json):
        super().__init__()
        self.update(schema.data)
        self._schema = schema

    @property
    @contract
    def schema(self) -> Json:
        return self._schema

    @abc.abstractmethod
    @contract
    def to_json(self, resource) -> Json:
        pass


class ListType(DataType):
    @contract
    def __init__(self, data_type: DataType):
        super().__init__(Json.from_data({
            'type': 'array',
            'items': data_type,
        }))
        self._data_type = data_type

    def to_json(self, resource):
        data = []
        for item in resource:
            data.append(self._data_type.to_json(item))
        return data


class IdentifiableDataType(DataType):
    """
    These are JSON Schemas that provide metadata so they can be aggregated and
    re-used throughout a schema. See InternalReferenceAggregator.
    """

    @contract
    def __init__(self, schema: Json, name: str, group_name: str = 'data'):
        super().__init__(schema)
        self._group_name = group_name
        self._name = name

    @property
    @contract
    def group_name(self) -> str:
        return self._group_name

    @property
    @contract
    def name(self) -> str:
        return self._name


class JsonSchema(Json):
    pass


@contract
def get_schema(url: str) -> Json:
    """
    Gets a JSON Schema from a URL.
    :param url:
    :return:
    :raises requests.HTTPError
    :raises json.decoder.JSONDecodeError
    """
    # @todo Will requiring HTTPS be enough for security?
    response = requests.get(url, headers={
        'Accept': 'application/schema+json; q=1, application/json; q=0.9, */*',
    })
    response.raise_for_status()
    return Json.from_data(response.json())


class Validator:
    def validate(self, subject: Json, schema: Optional[Json] = None):
        reference_resolver = RefResolver('', {})
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
        validate(data, schema)


class Rewriter(with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    @contract
    def rewrite(self, schema: Json) -> Json:
        pass


class IdentifiableDataTypeAggregator(Rewriter):
    """
    Rewrites a JSON Schema's IdentifiableDataTypes.
    """

    @contract
    def _rewrite_data_type(self, data_type: IdentifiableDataType,
                           definitions: Dict) -> Tuple:
        """
        Rewrites an InternalReference.
        """
        definitions.setdefault(data_type.group_name, {})
        if data_type.name not in definitions[data_type.group_name]:
            # Set a placeholder definition to avoid infinite loops.
            definitions[data_type.group_name][data_type.name] = {}
            # Rewrite the reference itself, because it may contain further
            # references.
            data, definitions = self._rewrite(
                data_type.schema.data, definitions)
            definitions[data_type.group_name][data_type.name] = data
        return {
            '$ref': '#/definitions/%s/%s' % (data_type.group_name,
                                             data_type.name),
        }, definitions

    def rewrite(self, schema):
        definitions = {
        } if 'definitions' not in schema.data else schema.data['definitions']
        data, definitions = self._rewrite(schema.data, definitions)
        # There is no reason we should omit empty definitions, except that
        #  existing code does not always expect them.
        if len(definitions) and len([x for x in definitions if len(x)]):
            data.setdefault('definitions', {})
            data['definitions'].update(definitions)
        return Json.from_data(data)

    @contract
    def _rewrite(self, data, definitions: Dict) -> Tuple:
        if isinstance(data, IdentifiableDataType):
            return self._rewrite_data_type(data, definitions)
        if isinstance(data, List):
            for index, item in enumerate(data):
                data[index], definitions = self._rewrite(item, definitions)
            return data, definitions
        elif isinstance(data, Dict):
            data = copy(data)
            for key, item in data.items():
                data[key], definitions = self._rewrite(item, definitions)
            return data, definitions
        return data, definitions


class ExternalReferenceProxy(Rewriter):
    """
    Rewrites JSON Schemas to proxy references through
    ExternalJsonSchemaEndpoint.
    """

    _REWRITE_KEYS = ('$ref', '$schema')

    @contract
    def __init__(self, base_url: str, urls: EndpointUrlBuilder):
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
        if pointer.startswith(self._base_url):
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

    def rewrite(self, schema: Json):
        data = self._rewrite(schema.data)
        if isinstance(schema.data, Dict) and 'id' in schema.data:
            data['id'] = self.rewrite_pointer(schema.data['id'])
        return Json.from_data(data)

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


class NestedRewriter(Rewriter):
    def __init__(self):
        super().__init__()
        self._rewriters = []

    @contract
    def add_rewriter(self, rewriter: Rewriter):
        self._rewriters.append(rewriter)

    def rewrite(self, schema):
        for rewriter in self._rewriters:
            schema = rewriter.rewrite(schema)
        return schema
