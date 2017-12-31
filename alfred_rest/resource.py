from typing import Iterable, Optional, Dict

from contracts import contract, ContractsMeta, with_metaclass

from alfred import format_iter
from alfred_rest.json import DataType, IdentifiableDataType, \
    IdentifiableScalarType


class ResourceIdType(IdentifiableScalarType):
    def __init__(self):
        super().__init__({
            'title': 'A resource ID',
            'type': 'string',
        }, 'resource-id')


class ResourceType(IdentifiableDataType):
    @contract
    def __init__(self, schema: Dict, *args, **kwargs):
        schema['type'] = 'object'
        schema.setdefault('properties', {})
        schema['properties']['id'] = ResourceIdType()
        schema.setdefault('required', [])
        schema['required'].append('id')
        super().__init__(schema, *args, **kwargs)


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
    @contract
    def get_type(self) -> ResourceType:
        pass

    @contract
    def get_resource(self, resource_id: str):
        pass

    @contract
    def get_resources(self) -> Iterable:
        pass


class ExpandableResourceRepository(ResourceRepository):
    @contract
    def get_add_type(self) -> DataType:
        pass

    @contract
    def add_resources(self, resources: Iterable) -> Iterable:
        pass


class ShrinkableResourceRepository(ResourceRepository):
    @contract
    def delete_resources(self, resources: Iterable):
        pass


class UpdateableResourceRepository(ResourceRepository):
    @contract
    def get_update_type(self) -> DataType:
        pass

    @contract
    def update_resources(self, resources: Iterable) -> Iterable:
        pass
