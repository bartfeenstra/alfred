import abc
from typing import Iterable, List, Dict

from contracts import contract, with_metaclass, ContractsMeta

from alfred_speech.schema import SchemaErrorBase


class SchemaTypeError(SchemaErrorBase, TypeError):
    pass


class SchemaValueError(SchemaErrorBase, ValueError):
    pass


class SchemaLookupError(SchemaErrorBase, LookupError):
    pass


class SchemaIndexError(SchemaLookupError, IndexError):
    pass


class SchemaKeyError(SchemaLookupError, KeyError):
    pass


class SchemaAttributeError(SchemaErrorBase, AttributeError):
    pass


class Schema(with_metaclass(ContractsMeta)):
    def assert_valid(self, value):
        for error in self.validate(value):
            raise error

    @contract
    def is_valid(self, value) -> bool:
        for _ in self.validate(value):
            return False
        return True

    @abc.abstractmethod
    @contract
    def validate(self, value) -> Iterable:
        pass

    @contract
    def get_instance(self, value, schema_type: type):
        """
        Returns an instance of the specified schema type.
        None is returned if the schema does not contain a schema of this type.
        The schema itself, or any contained schema may be returned.

        :type value: *
        :rtype: alfred_speech.schema.validate.Schema|None
        """
        if Schema not in schema_type.__mro__:
            raise ValueError()
        if isinstance(self, schema_type):
            return self
        return None


class AnySchema(Schema):
    def validate(self, value):
        return []


class TypeSchema(Schema):
    @contract
    def __init__(self, type: type):
        self._type = type

    def validate(self, value):
        if not isinstance(value, self._type):
            return [SchemaTypeError()]
        return []


class ListSchema(Schema):
    def __init__(self, item_schema: Schema, min_length: int = 0,
                 max_length: int = None):
        super().__init__()
        self._item_schema = item_schema
        self._min_length = min_length
        self._max_length = max_length

    def validate(self, value) -> Iterable:
        if not isinstance(value, List):
            yield SchemaTypeError()
            return
        if len(value) < self._min_length:
            yield SchemaValueError()
        if self._max_length and len(value) > self._max_length:
            yield SchemaValueError()
        for index, item in enumerate(value):
            for error in self._item_schema.validate(item):
                error.add_parent_container_item_id(index)
                yield error


class DictSchema(Schema):
    def __init__(self, item_schemas: Dict, limit_required_keys=None,
                 allow_additional_keys=False):
        super().__init__()
        self._item_schemas = item_schemas
        self._allow_additional_keys = allow_additional_keys
        self._limit_required_keys = limit_required_keys

    def validate(self, value) -> Iterable:
        if not isinstance(value, Dict):
            yield SchemaTypeError()
            return
        if not self._allow_additional_keys and set(value.keys()) - set(
                self._item_schemas.keys()):
            yield SchemaValueError()
        for key, schema in self._item_schemas.items():
            if key not in value:
                if self._limit_required_keys is None or self._limit_required_keys is not None and key in self._limit_required_keys:
                    error = SchemaValueError()
                    error.add_parent_container_item_id(key)
                    yield error
                continue
            for error in schema.validate(value[key]):
                error.add_parent_container_item_id(key)
                yield error
