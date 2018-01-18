import abc
from typing import Dict, Callable

from contracts import contract


class DataType:
    @abc.abstractmethod
    @contract
    def get_json_schema(self) -> Dict:
        pass


class OutputDataType(DataType):
    @abc.abstractmethod
    def to_json(self, data):
        pass


class InputDataType(DataType):
    @abc.abstractmethod
    def from_json(self, json_data):
        pass


class InputProcessorType(InputDataType):
    @contract
    def __init__(self, data_type: InputDataType, processor: Callable):
        self._type = data_type
        self._processor = processor

    def get_json_schema(self):
        return self._type.get_json_schema()

    def from_json(self, json_data):
        return self._processor(self._type.from_json(json_data))


class OutputProcessorType(OutputDataType):
    @contract
    def __init__(self, data_type: OutputDataType, processor: Callable):
        self._type = data_type
        self._processor = processor

    def get_json_schema(self):
        return self._type.get_json_schema()

    def to_json(self, data):
        return self._type.to_json(self._processor(data))


class ScalarType(OutputDataType, InputDataType):
    @contract
    def __init__(self, schema: Dict):
        self._assert_valid_scalar_type(schema)
        self._schema = schema

    def get_json_schema(self):
        return self._schema

    def from_json(self, data):
        return data

    def to_json(self, data):
        return data

    @staticmethod
    @contract
    def _assert_valid_scalar_type(schema: Dict):
        if 'enum' in schema:
            for value in schema['enum']:
                if not isinstance(value,
                                  (str, int, float, bool)) or value is None:
                    raise ValueError(
                        'This type must be a scalar, but an enum with %s "%s" was given.' % (
                            type(value), value))
            return
        if 'type' in schema:
            if schema['type'] not in ('string', 'number', 'boolean'):
                raise ValueError(
                    'This type must be a scalar, but %s was given.' %
                    schema['type'])
            return
        raise ValueError('Schema does not represent a scalar value.')


class ListType(InputDataType, OutputDataType):
    @contract
    def __init__(self, item_type: DataType):
        self._schema = {
            'type': 'array',
            'items': item_type,
        }
        self._item_type = item_type

    def get_json_schema(self):
        return self._schema

    def from_json(self, json_data):
        assert isinstance(self._item_type, InputDataType)
        return list(map(self._item_type.from_json, json_data))

    def to_json(self, data):
        assert isinstance(self._item_type, OutputDataType)
        return list(map(self._item_type.to_json, data))


class IdentifiableDataType(DataType):
    """
    These are JSON Schemas that provide metadata so they can be aggregated and
    re-used throughout a schema. See IdentifiableDataTypeAggregator.
    """

    @contract
    def __init__(self, name: str, group_name: str = 'data'):
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


class IdentifiableScalarType(IdentifiableDataType, ScalarType):
    pass
