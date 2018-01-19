import abc
from typing import Iterable, Optional, Dict, Union

from contracts import contract, ContractsMeta, with_metaclass

from alfred import format_iter
from alfred_json.type import IdentifiableDataType, IdentifiableScalarType, \
    OutputDataType, InputDataType


class ResourceIdType(IdentifiableScalarType):
    def __init__(self):
        super().__init__('resource-id')

    def get_json_schema(self):
        return {
            'title': 'A resource ID',
            'type': 'string',
        }


class ResourceNotFound(RuntimeError):
    def __init__(self, resource_name: str,
                 available_resources: Optional[Dict] = None):
        available_resources = available_resources if available_resources is not None else {}
        if not available_resources:
            message = 'Could not find resource "%s", because there are no resources.' % resource_name
        else:
            message = 'Could not find resource "%s". Did you mean one of the following?\n' % resource_name + \
                      format_iter(available_resources.keys())
        super().__init__(message)


class ResourceRepository(with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    def get_type(self) -> Union[OutputDataType, IdentifiableDataType]:
        pass

    @abc.abstractmethod
    @contract
    def get_resource(self, resource_id: str):
        pass

    @abc.abstractmethod
    @contract
    def get_resources(self) -> Iterable:
        pass


class ExpandableResourceRepository(ResourceRepository):
    @abc.abstractmethod
    def get_add_type(self) -> Union[InputDataType, IdentifiableDataType]:
        pass

    @abc.abstractmethod
    @contract
    def add_resources(self, resources: Iterable) -> Iterable:
        pass


class ShrinkableResourceRepository(ResourceRepository):
    @abc.abstractmethod
    @contract
    def delete_resources(self, resources: Iterable):
        pass


class UpdateableResourceRepository(ResourceRepository):
    @abc.abstractmethod
    def get_update_type(self) -> Union[InputDataType, IdentifiableDataType]:
        pass

    @abc.abstractmethod
    @contract
    def update_resources(self, resources: Iterable) -> Iterable:
        pass
