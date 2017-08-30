import abc
from typing import Iterable, List

from contracts import contract

"""
The Schema API provides a unified API for the following data processing tasks:
1) Validation
    All schemas are self-validating.
2) Traversal and reading
4) Mutation
    Using Mutator for the schemas that support it.
5) Additional metadata
    Through the schemas that support it.
The API aims to be layered, in the sense that if you want validation only, you
should not have to deal with any of the other layers. 

The API tries to be as lazy as possible by using generators. If you need to
read iterable API output more than one, wrap it in ensure_list() before you do
so. Processing iterators with this API is unsupported, as its purpose is to
traverse iterables, which inherently exhausts any Iterator.
"""


@contract
def ensure_list(iterable: Iterable) -> List:
    if isinstance(iterable, List):
        return iterable
    return list(iterable)


class SchemaError(BaseException):
    @property
    @abc.abstractmethod
    @contract
    # @todo Update this to use tuples with schema+data+selectors, if possible.
    def parent_container_item_ids(self) -> Iterable:
        pass

    @abc.abstractmethod
    def add_parent_container_item_id(self, id):
        pass


class SchemaErrorBase(SchemaError):
    def __init__(self):
        self._parent_container_item_ids = []

    def parent_container_item_ids(self) -> Iterable:
        return self._parent_container_item_ids

    def add_parent_container_item_id(self, id):
        self._parent_container_item_ids.insert(0, id)
