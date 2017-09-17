import abc
from copy import copy
from typing import Iterable, Dict

from contracts import contract

from alfred_speech.schema.mutate import NonSettableValueError, \
    NonDeletableValueError, DictLikeSchema
from alfred_speech.schema.traverse import RuntimeSchema, CompositeSchema
from alfred_speech.schema.validate import Schema, SchemaValueError, \
    SchemaTypeError, SchemaAttributeError


class EnumSchema(Schema):
    def validate(self, value):
        for option in self._enum:
            if value == option:
                return []
        return [SchemaValueError()]

    @property
    @abc.abstractmethod
    @contract
    def _enum(self) -> Iterable:
        pass


class IntrospectiveEnumSchema(Schema):
    @property
    @abc.abstractmethod
    @contract
    def enum(self) -> Iterable:
        """
        :return: Items are Tuple[Any, str], containing the enum value and its
         human-readable label.
        """
        pass


class IntrospectiveWhitelistSchema(EnumSchema, IntrospectiveEnumSchema):
    @contract
    def __init__(self, whitelist: Iterable):
        self._whitelist = whitelist

    @property
    def _enum(self):
        for option in self._whitelist:
            yield option[0]

    @property
    def enum(self):
        return self._whitelist


class RangeSchema(Schema):
    def __init__(self, min=None, max=None):
        self._min = min
        self._max = max

    def validate(self, value):
        if self._min is not None and value < self._min:
            yield SchemaValueError()
        if self._max is not None and value > self._max:
            yield SchemaValueError()


class AndSchema(CompositeSchema):
    def __init__(self, schemas: Iterable):
        self._schemas = schemas

    def get_schemas(self):
        return self._schemas


class OrSchema(RuntimeSchema):
    @contract
    def __init__(self, schemas: Iterable):
        self._schemas = schemas

    def validate(self, value):
        errors = []
        for schema in self._schemas:
            schema_errors = list(schema.validate(value))
            if not schema_errors:
                return []
            errors.extend(schema_errors)
        # @todo Consider returning a more useful error explaining the behavior of this OR schema.
        return errors

    def get_schema(self, value):
        schemas = []
        for schema in self._schemas:
            if not list(schema.validate(value)):
                schemas.extend(schema)
        if not schemas:
            return None
        if 0 == len(schemas):
            return schemas[0]
        return AndSchema(schemas)


class EqualsSchema(Schema):
    def __init__(self, value):
        self._value = value

    def validate(self, value):
        if self._value != value:
            return [SchemaValueError()]
        return []


class NullableSchema(OrSchema):
    @contract
    def __init__(self, nullable_type: Schema):
        super().__init__([EqualsSchema(None), nullable_type])


class ObjectAttributeSchema(DictLikeSchema):
    def __init__(self, object_type, attribute_schemas: Dict):
        super().__init__()
        self._attribute_schemas = attribute_schemas
        self._object_type = object_type

    def validate(self, value) -> Iterable:
        if not isinstance(value, self._object_type):
            yield SchemaTypeError()
            return
        for attribute, attribute_schema in self._attribute_schemas.items():
            for error in attribute_schema.validate(getattr(value, attribute)):
                error.add_parent_container_item_id(attribute)
                yield error

    def get_schema(self, selector):
        return self._attribute_schemas[selector]

    def get_schemas(self):
        return self._attribute_schemas

    def assert_valid_selector(self, selector):
        if selector not in self._attribute_schemas:
            raise SchemaAttributeError()

    def set_value(self, data, selector, value):
        if selector not in self._attribute_schemas:
            raise SchemaAttributeError()
        if not self._mutable:
            raise NonSettableValueError()
        copied_data = copy(data)
        setattr(copied_data, selector, value)
        self.assert_valid(copied_data)
        setattr(data, selector, value)

    def set_values(self, data, values):
        if not self._mutable:
            raise NonSettableValueError()
        copied_data = copy(data)
        for attribute in self._attribute_schemas.keys():
            setattr(copied_data, attribute, values[attribute])
        self.assert_valid(copied_data)
        for attribute in self._attribute_schemas.keys():
            setattr(data, attribute, values[attribute])

    def get_value(self, data, key):
        self.assert_valid(data)
        if key not in self._attribute_schemas:
            raise SchemaAttributeError()
        return getattr(data, key)

    def get_values(self, data):
        self.assert_valid(data)
        items = {}
        for attribute in self._attribute_schemas.keys():
            items[attribute] = getattr(data, attribute)
        return items

    def delete_value(self, data, selector):
        if selector not in self._attribute_schemas:
            raise SchemaAttributeError()
        if not self._mutable:
            raise NonDeletableValueError()
        copied_data = copy(data)
        delattr(copied_data, selector)
        self.assert_valid(copied_data)
        delattr(data, selector)

    def delete_values(self, data):
        if not self._mutable:
            raise NonDeletableValueError()
        copied_data = copy(data)
        for attribute in self._attribute_schemas.keys():
            delattr(copied_data, attribute)
        self.assert_valid(copied_data)
        for attribute in self._attribute_schemas.keys():
            delattr(data, attribute)

# class Base64Schema(OneToOneDataReaderSchema):
#     def validate(self, value):
#         base64.b64decode(value)
#
#     def get_value(self, data):
#         self.assert_valid(data)
#         return base64.b64decode(data)
