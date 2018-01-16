import abc
from typing import List, Iterator, Iterable, Dict

from contracts import contract, with_metaclass, ContractsMeta

from alfred_speech.schema import validate
from alfred_speech.schema.validate import Schema, SchemaIndexError, SchemaKeyError, SchemaLookupError

"""
This module provides traversable schemas. Custom schemas can implement the
*LikeSchema types, or you can use the other *Schema classes directly. Use
*Traverser to find subsets of schemas using selectors.
"""


class _ValueContainerSchema(Schema):
    @abc.abstractmethod
    def assert_valid_selector(self, selector):
        """
        May raise SchemaLookupError.
        """
        pass

    @contract
    def is_valid_selector(self, selector) -> bool:
        try:
            self.assert_valid_selector(selector)
            return True
        except SchemaLookupError:
            return False

    @abc.abstractmethod
    def get_value(self, value, selector):
        """
        May raise SchemaLookupError.
        """
        pass


class ListLikeSchema(_ValueContainerSchema):
    @abc.abstractmethod
    @contract
    def get_schema(self) -> Schema:
        pass

    @abc.abstractmethod
    @contract
    def get_values(self, value) -> List:
        pass


class DictLikeSchema(_ValueContainerSchema):
    @abc.abstractmethod
    @contract
    def get_schema(self, selector) -> Schema:
        """
        May raise SchemaLookupError.
        """
        pass

    @abc.abstractmethod
    @contract
    def get_values(self, value) -> Dict:
        pass


class RuntimeSchema(Schema):
    """
    A run-time self-resolving schema.

    A run-time schema MUST NOT be the cause of a failed traversal. Traversers
    MUST resolve the run-time schema and continue performing their action on
    the returned schema.
    """

    @abc.abstractmethod
    def get_schema(self, value):
        """

        :param value:
        :return: Schema or None
        """
        pass

    def validate(self, value):
        return self.get_schema(value).validate(value)

    def get_instance(self, value, schema_type):
        instance = super().get_instance(value, schema_type)
        if instance is not None:
            return instance
        runtime_schema = self.get_schema(value)
        # Check inheritance directly for validation-only types.
        if isinstance(runtime_schema, schema_type):
            return runtime_schema
        # Check inheritance for traversal types.
        if isinstance(runtime_schema, Schema):
            return runtime_schema.get_instance(value, schema_type)
        return None


class CompositeSchema(Schema):
    @abc.abstractmethod
    @contract
    def get_schemas(self) -> Iterable:
        pass

    def validate(self, value):
        for schema in self.get_schemas():
            for error in schema.validate(value):
                yield error

    def get_instance(self, value, schema_type):
        instance = super().get_instance(value, schema_type)
        if instance is not None:
            return instance
        for composite_schema in self.get_schemas():
            # Check inheritance directly for validation-only types.
            if isinstance(composite_schema, schema_type):
                return composite_schema
            # Check inheritance for traversal types.
            if isinstance(composite_schema, Schema):
                instance = composite_schema.get_instance(value, schema_type)
                if instance is not None:
                    return instance
        return None


class ListSchema(validate.ListSchema, ListLikeSchema):
    def get_schema(self):
        return self._item_schema

    def assert_valid_selector(self, selector):
        if not isinstance(selector, int):
            raise SchemaIndexError()

    def get_value(self, value, selector):
        self.assert_valid(value)
        return value[selector]

    def get_values(self, value):
        self.assert_valid(value)
        return value


class DictSchema(validate.DictSchema, DictLikeSchema):
    def get_schema(self, selector):
        return self._item_schemas[selector]

    def get_schemas(self):
        return self._item_schemas

    def assert_valid_selector(self, selector):
        if selector not in self._item_schemas:
            raise SchemaKeyError()

    def get_value(self, value, selector):
        self.assert_valid(value)
        if selector not in self._item_schemas:
            raise SchemaKeyError()
        return value[selector]

    def get_values(self, value):
        self.assert_valid(value)
        items = {}
        for key in self._item_schemas.keys():
            items[key] = value[key]
        return items


class Traverser(with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    @contract
    def ancestors(self, schema: Schema, data, selectors) -> List:
        """
        Returns the specified schema and its ancestors.

        May raise SchemaLookupError if the specified selectors do not exist.
        """
        pass


class CoreTraverser(Traverser):
    def ancestors(self, schema, data, selectors):
        schema.assert_valid(data)
        # Cast the iterator to a list, so we can keep the internals lazy, but
        # return an iterable that is guaranteed to be correct and complete.
        return list(self._ancestors_inclusive(schema, data, selectors, ()))

    @contract
    def _ancestors_inclusive(self, schema: Schema, data, remaining_selectors,
                             ancestral_selectors) -> Iterator:
        yield schema, data, ancestral_selectors
        for ancestor in self._ancestors_exclusive(schema, remaining_selectors,
                                                  data, ancestral_selectors):
            yield ancestor

    @contract
    def _ancestors_exclusive(self, schema: Schema, remaining_selectors, data,
                             ancestral_selectors) -> Iterator:
        if not remaining_selectors:
            return

        if isinstance(schema, ListLikeSchema):
            current_selector = remaining_selectors[0]
            schema.assert_valid_selector(current_selector)
            remaining_selectors = remaining_selectors[1:]
            ancestral_selectors = ancestral_selectors + (current_selector,)
            data = data[current_selector]
            schema = schema.get_schema()
            yield schema, data, ancestral_selectors
            for ancestor in self._ancestors_exclusive(schema,
                                                      remaining_selectors,
                                                      data,
                                                      ancestral_selectors):
                yield ancestor
            return

        if isinstance(schema, DictLikeSchema):
            current_selector = remaining_selectors[0]
            schema.assert_valid_selector(current_selector)
            remaining_selectors = remaining_selectors[1:]
            ancestral_selectors = ancestral_selectors + (current_selector,)
            data = data.get(current_selector)
            schema = schema.get_schema(current_selector)
            yield schema, data, ancestral_selectors
            for ancestor in self._ancestors_exclusive(schema,
                                                      remaining_selectors,
                                                      data,
                                                      ancestral_selectors):
                yield ancestor
            return

        if isinstance(schema, CompositeSchema):
            for possible_schema in schema.get_schemas():
                try:
                    # Cast the iterator to a list, so we can keep the internals lazy, but
                    # return an iterable that is guaranteed to be correct and complete.
                    ancestors = list(self._ancestors_exclusive(possible_schema,
                                                               remaining_selectors,
                                                               data,
                                                               ancestral_selectors))
                    for ancestor in ancestors:
                        yield ancestor
                    return
                except SchemaLookupError:
                    continue
            raise SchemaLookupError()

        if isinstance(schema, RuntimeSchema):
            schema = schema.get_schema(data)
            for ancestor in self._ancestors_exclusive(schema,
                                                      remaining_selectors,
                                                      data,
                                                      ancestral_selectors):
                yield ancestor
            return

        raise SchemaLookupError()
