import abc
from typing import Iterable, Optional, Dict, Union, Callable

from contracts import contract, ContractsMeta, with_metaclass

from alfred import format_iter
from alfred_http.endpoints import BadRequestError
from alfred_json.type import IdentifiableDataType, IdentifiableScalarType, \
    OutputDataType, InputDataType, UpdateInputDataType, OneOfComplexType


class ResourceIdType(IdentifiableScalarType):
    def __init__(self):
        super().__init__('resource-id')

    def get_json_schema(self):
        return {
            'title': 'A resource ID',
            'type': 'string',
        }


class ResourceType(IdentifiableDataType, UpdateInputDataType, OutputDataType):
    """
    Describes a resource to the REST API.

    A resource is a data type of which zero or more can exist, and which can be
    retrieved through the HTTP API.

    Resource types can extend this class, and optionally extend Input
    """

    def get_json_schema(self):
        return {
            'type': 'object',
            'properties': {
                'id': ResourceIdType(),
            },
            'required': ['id'],
        }

    def update_from_json(self, json_data, instance):
        if instance.id != json_data['id']:
            raise BadRequestError()

    def to_json(self, data):
        try:
            return {
                'id': data.id,
            }
        except AttributeError:
            raise ValueError('Resources must have an "id" property.')


class AnyResourceType(ResourceType, InputDataType, UpdateInputDataType):
    @contract
    def __init__(self, resource_type: ResourceType, concrete_name_key: str, concrete_type_name_extractor: Callable):
        ResourceType.__init__(self, resource_type.name)
        self._subtype = OneOfComplexType(resource_type, concrete_name_key, concrete_type_name_extractor)

    def add_concrete_type(self, data_type: ResourceType):
        self._subtype.add_concrete_type(data_type)

    def from_json(self, json_data):
        return self._subtype.from_json(json_data)

    def update_from_json(self, json_data, instance):
        self._subtype.update_from_json(json_data, instance)

    def to_json(self, data):
        return self._subtype.to_json(data)


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
    """
    Allows internal data as to be retrieved through the REST-ful HTTP API.
    Register child classes as Extension services with the "resources" tag, and
    HTTP GET endpoints will be available automatically.
    """

    @abc.abstractmethod
    def get_type(self) -> ResourceType:
        pass

    @abc.abstractmethod
    @contract
    def get_resource(self, resource_id: str):
        pass

    @abc.abstractmethod
    @contract
    def get_resources(self, ids=None, filters: Iterable=()) -> Iterable:
        pass


class ExpandableResourceRepository(ResourceRepository):
    """
    Allows internal data as to be added through the REST-ful HTTP API.
    Register child classes as Extension services with the "resources" tag, and
    HTTP POST endpoints will be available automatically.
    """

    @abc.abstractmethod
    def get_add_type(self) -> Union[InputDataType, ResourceType]:
        pass

    @abc.abstractmethod
    def add_resource(self, resource):
        pass

    @abc.abstractmethod
    @contract
    def add_resources(self, resources: Iterable) -> Iterable:
        pass


class ShrinkableResourceRepository(ResourceRepository):
    """
    Allows internal data as to be deleted through the REST-ful HTTP API.
    Register child classes as Extension services with the "resources" tag, and
    HTTP DELETE endpoints will be available automatically.
    """

    @abc.abstractmethod
    def delete_resource(self, resource):
        pass

    @abc.abstractmethod
    @contract
    def delete_resources(self, resources: Iterable):
        pass


class UpdateableResourceRepository(ResourceRepository):
    """
    Allows internal data as to be changed through the REST-ful HTTP API.
    Register child classes as Extension services with the "resources" tag, and
    HTTP UPDATE (and optionally PATCH) endpoints will be available
    automatically.
    """

    def get_update_type(self) -> Union[ResourceType, UpdateInputDataType]:
        """
        If the returned type also extends OutputDataType, HTTP PATCH endpoints
        will be available automatically.
        :return:
        """
        return self.get_type()

    @abc.abstractmethod
    def update_resource(self, resource):
        pass

    @abc.abstractmethod
    @contract
    def update_resources(self, resources: Iterable) -> Iterable:
        pass
