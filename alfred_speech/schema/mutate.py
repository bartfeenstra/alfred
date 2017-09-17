import abc
from copy import copy
from typing import Dict, Iterable

from contracts import contract, with_metaclass, ContractsMeta

from alfred_speech.schema import traverse
from alfred_speech.schema.validate import SchemaTypeError, Schema, \
    SchemaKeyError


class ImmutableValueError(SchemaTypeError):
    pass


class NonSettableValueError(ImmutableValueError):
    """
    Raised if a value cannot be set.
    """
    pass


class NonDeletableValueError(ImmutableValueError):
    """
    Raised if a value cannot be deleted.
    """
    pass


class MutableSchema(Schema):
    """
    All child classes may raise SchemaTypeError if write attempts are made to
    immutable data.
    """

    def __init__(self):
        self._mutable = False

    @property
    @contract
    def mutable(self) -> bool:
        return self._mutable

    @mutable.setter
    @contract
    def mutable(self, mutable: bool):
        self._mutable = mutable

    @abc.abstractmethod
    @contract
    def delete_values(self, data) -> None:
        """
        May raise NonDeletableValueError.
        """
        pass


class ListLikeSchema(traverse.ListLikeSchema, MutableSchema):
    @abc.abstractmethod
    @contract
    def set_value(self, data, selector: int, value) -> None:
        """
        May raise NonSettableValueError.
        """
        pass

    @abc.abstractmethod
    @contract
    def set_values(self, data, values: Iterable) -> None:
        """
        May raise NonSettableValueError.
        """
        pass

    @abc.abstractmethod
    @contract
    def delete_value(self, data, selector: int) -> None:
        """
        May raise NonDeletableValueError.
        """
        pass


class DictLikeSchema(traverse.DictLikeSchema, MutableSchema):
    @abc.abstractmethod
    @contract
    def set_value(self, data, selector: str, value) -> None:
        """
        May raise NonSettableValueError.
        """
        pass

    @abc.abstractmethod
    @contract
    def set_values(self, data, values: Dict) -> None:
        """
        May raise NonSettableValueError.
        """
        pass

    @abc.abstractmethod
    @contract
    def delete_value(self, data, selector: str) -> None:
        """
        May raise NonDeletableValueError.
        """
        pass


class ListSchema(traverse.ListSchema, ListLikeSchema):
    def set_value(self, data, selector, value):
        self.assert_valid(data)
        if not self._mutable:
            raise NonSettableValueError()
        copied_data = copy(data)
        copied_data.insert(selector, value)
        self.assert_valid(copied_data)
        data.insert(selector, value)

    def set_values(self, data, values):
        self.assert_valid(data)
        if not self._mutable:
            raise NonSettableValueError()
        self.assert_valid(values)
        while data:
            del(data[0])
        for value in values:
            data.append(value)

    def delete_value(self, data, selector):
        self.assert_valid(data)
        if not self._mutable:
            raise NonDeletableValueError()
        copied_data = copy(data)
        del copied_data[selector]
        self.assert_valid(copied_data)
        del data[selector]

    def delete_values(self, data):
        self.assert_valid(data)
        if not self._mutable:
            raise NonDeletableValueError()
        self.assert_valid([])
        while data:
            del(data[0])


class DictSchema(traverse.DictSchema, DictLikeSchema):
    def set_value(self, data, selector, value):
        self.assert_valid(data)
        if selector not in self._item_schemas:
            raise SchemaKeyError()
        if not self._mutable:
            raise NonSettableValueError()
        copied_data = copy(data)
        copied_data[selector] = value
        self.assert_valid(copied_data)
        data[selector] = value

    def set_values(self, data, values):
        self.assert_valid(data)
        if not self._mutable:
            raise NonSettableValueError()
        copied_data = copy(data)
        for selector in self._item_schemas.keys():
            copied_data[selector] = values[selector]
        self.assert_valid(copied_data)
        for selector in self._item_schemas.keys():
            data[selector] = values[selector]

    def delete_value(self, data, selector):
        self.assert_valid(data)
        if selector not in self._item_schemas:
            raise SchemaKeyError()
        if not self._mutable:
            raise NonDeletableValueError()
        copied_data = copy(data)
        del copied_data[selector]
        self.assert_valid(copied_data)
        del data[selector]

    def delete_values(self, data):
        self.assert_valid(data)
        if not self._mutable:
            raise NonDeletableValueError()
        copied_data = copy(data)
        for selector in self._item_schemas.keys():
            del copied_data[selector]
        self.assert_valid(copied_data)
        for selector in self._item_schemas.keys():
            del data[selector]


class Mutator(with_metaclass(ContractsMeta)):
    def set_value(self):
        pass
