import abc
from copy import copy
from typing import Dict, List, Tuple, Iterable, Optional
from urllib.parse import urlunsplit, urlsplit

from contracts import contract, ContractsMeta, with_metaclass
from jsonschema import validate
from jsonschema.validators import validator_for

from alfred import format_iter
from alfred_http.endpoints import EndpointUrlBuilder
from alfred_rest import base64_encodes


class DataType(dict):
    @abc.abstractmethod
    def to_json(self, resource):
        pass


class ListType(DataType):
    @contract
    def __init__(self, data_type: DataType):
        super().__init__({
            'type': 'array',
            'items': data_type,
        })
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
    def __init__(self, schema: Dict, name: str, group_name: str = 'data'):
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


class Rewriter(with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    @contract
    def rewrite(self, schema: Dict) -> Dict:
        pass


class IdentifiableDataTypeAggregator(Rewriter):
    """
    Rewrites a JSON Schema's IdentifiableDataTypes.
    """

    def __init__(self, urls: EndpointUrlBuilder):
        self._schema_url = urls.build('schema')

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
            schema, definitions = self._rewrite(dict(data_type), definitions)
            definitions[data_type.group_name][data_type.name] = schema
        return {
            '$ref': '%s#/definitions/%s/%s' % (self._schema_url,
                                               data_type.group_name,
                                               data_type.name),
        }, definitions

    def rewrite(self, schema):
        definitions = {} if 'definitions' not in schema else schema['definitions']
        schema, definitions = self._rewrite(schema, definitions)
        # There is no reason we should omit empty definitions, except that
        #  existing code does not always expect them.
        if len(definitions) and len([x for x in definitions if len(x)]):
            schema.setdefault('definitions', {})
            schema['definitions'].update(definitions)
        return schema

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

    _REWRITE_KEYS = ('id', '$ref', '$schema')

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

    def rewrite(self, schema):
        schema = self._rewrite(schema)
        if 'id' in schema:
            schema['id'] = self.rewrite_pointer(schema['id'])
        return schema

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


class Validator:
    def __init__(self, rewriter: Rewriter):
        self._rewriter = rewriter

    @contract
    def validate(self, subject, schema: Dict):
        schema = self._rewriter.rewrite(schema)
        validate(subject, schema)


class SchemaNotFound(RuntimeError):
    def __init__(self, schema_id: str,
                 available_schemas: Optional[Dict] = None):
        available_schemas = available_schemas if available_schemas is not None else {}
        if not available_schemas:
            message = 'Could not find schema "%s", because there are no schemas.' % schema_id
        else:
            message = 'Could not find schema "%s". Did you mean one of the following?\n' % schema_id + \
                      format_iter(available_schemas.keys())
        super().__init__(message)


class SchemaRepository(with_metaclass(ContractsMeta)):
    def __init__(self):
        self._schemas = {}

    @contract
    def add_schema(self, schema: Dict):
        cls = validator_for(schema)
        cls.check_schema(schema)
        assert 'id' in schema
        assert schema['id'] not in self._schemas
        self._schemas[schema['id']] = schema

    def get_schema(self, schema_id: str) -> Optional[Dict]:
        try:
            return self._schemas[schema_id]
        # If we cannot find an exact match, try the ID with or without an empty
        # fragment.
        except KeyError:
            if '#' == schema_id[-1]:
                schema_id = schema_id[0:-1]
            elif '#' not in schema_id:
                schema_id += '#'
            else:
                # This repository does not (yet?) support subschemas.
                raise SchemaNotFound(schema_id, self._schemas)
            try:
                return self._schemas[schema_id]
            except KeyError:
                raise SchemaNotFound(schema_id, self._schemas)

    @contract
    def get_schemas(self) -> Iterable:
        return list(self._schemas.values())
