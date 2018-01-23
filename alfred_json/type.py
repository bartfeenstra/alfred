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


class UpdateInputDataType(DataType):
    @abc.abstractmethod
    def update_from_json(self, json_data, instance):
        pass


class IdentifiableDataType(DataType):
    """
    These are JSON Schemas that provide metadata so they can be aggregated and
    re-used throughout a schema. See IdentifiableDataTypeAggregator.
    """

    @contract
    def __init__(self, name: str):
        self._name = name

    @property
    @contract
    def name(self) -> str:
        return self._name


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


class IdentifiableScalarType(IdentifiableDataType, ScalarType):
    pass


class OneOfComplexType(InputDataType, UpdateInputDataType, OutputDataType):
    @contract
    def __init__(self, shared_type: DataType, concrete_type_name_key: str,
                 concrete_type_name_extractor: Callable):
        base_schema = shared_type.get_json_schema()
        assert 'object' == base_schema['type']
        assert concrete_type_name_key in base_schema['properties']
        assert concrete_type_name_key in base_schema['required']
        self._shared_type = shared_type
        self._concrete_type_name_key = concrete_type_name_key
        self._concrete_type_name_extractor = concrete_type_name_extractor
        self._concrete_types = {}

    def add_concrete_type(self, concrete_type: IdentifiableDataType):
        if self._shared_type:
            assert isinstance(concrete_type, self._shared_type.__class__)
        assert concrete_type.name not in self._concrete_types
        self._concrete_types[concrete_type.name] = concrete_type

    def get_json_schema(self):
        return {
            'allOf': [
                self._shared_type.get_json_schema(),
                {
                    'oneOf': map(lambda x: x.get_json_schema(),
                                 self._concrete_types)
                },
            ]

        }

    def from_json(self, json_data):
        return self._concrete_types[
            json_data[self._concrete_type_name_key]].from_json(json_data)

    def update_from_json(self, json_data, instance):
        return self._concrete_types[
            json_data[self._concrete_type_name_key]].update_from_json(
            json_data, instance)

    def to_json(self, data):
        concrete_type_name = self._concrete_type_name_extractor(data)
        concrete_type = self._concrete_types[concrete_type_name]
        return concrete_type.to_json(data)


# @todo Do we still need this?
# class OneOfType(InputDataType, OutputDataType):
#     def __init__(self):
#         self._data_types = []
#
#     def add_type(self, data_type: DataType):
#         self._data_types.append(data_type)
#
#     def get_json_schema(self):
#         return {
#             'oneOf': list(map(DataType.get_json_schema, self._data_types))
#         }
#
#     def from_json(self, json_data):
#         requirements = []
#         for data_type in self._data_types:
#             try:
#                 return data_type.from_json(json_data)
#             except Exception:
#                 requirements.append(
#                     indent(traceback.format_exc()))
#         message = "Cannot consume JSON. One of the following requirements must be met:\n"
#         message += "\n OR \n".join(requirements)
#         raise RuntimeError(message)
#
#     def to_json(self, data):
#         requirements = []
#         for data_type in self._data_types:
#             try:
#                 return data_type.to_json(data)
#             except Exception:
#                 requirements.append(
#                     indent(traceback.format_exc()))
#         message = "Cannot produce JSON. One of the following requirements must be met:\n"
#         message += "\n OR \n".join(requirements)
#         raise RuntimeError(message)


# @todo Do we still need this?
# class SubtypedType(InputDataType, UpdateInputDataType, OutputDataType):
#     @contract
#     def __init__(self, base_type: DataType):
#         self._base_type = base_type
#         self._subtypes = OneOfType()
#
#     def add_type(self, data_type: DataType):
#         assert isinstance(data_type, self._base_type.__class__)
#         self._subtypes.add_type(data_type)
#
#     def get_json_schema(self):
#         return {
#             'allOf': [
#                 self._base_type,
#                 self._subtypes,
#             ],
#         }
#
#     def from_json(self, json_data):
#         return self._subtypes.from_json(json_data)
#
#     def update_from_json(self, json_data, instance):
#         self._subtypes.update_from_json(json_data, instance)
#
#     def to_json(self, data):
#         return self._subtypes.to_json(data)


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
