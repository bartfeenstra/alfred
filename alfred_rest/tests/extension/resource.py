from typing import Iterable

from contracts import contract

from alfred_json.type import IdentifiableDataType, OutputDataType, \
    InputDataType
from alfred_rest.resource import ResourceNotFound, \
    ShrinkableResourceRepository, ExpandableResourceRepository, ResourceIdType


class RestTestResource:
    @contract
    def __init__(self, resource_id: str, label=''):
        self._id = resource_id
        self._label = label

    @property
    def id(self):
        return self._id

    @property
    def label(self):
        return self._label


class RestTestResourceType(IdentifiableDataType, OutputDataType):
    def __init__(self):
        super().__init__('rest-test')

    def get_json_schema(self):
        return {
            'type': 'object',
            'properties': {
                'id': ResourceIdType(),
                'label': {
                    'type': 'string',
                },
            },
            'required': ['id'],
        }

    def to_json(self, data):
        assert isinstance(data, RestTestResource)
        return {
            'id': data.id,
            'label': data.label,
        }


class AddRestTestResourceType(IdentifiableDataType, InputDataType):
    def __init__(self):
        super().__init__('rest-test-add')

    def get_json_schema(self):
        return {
            'type': 'object',
            'properties': {
                'id': ResourceIdType(),
                'label': {
                    'type': 'string',
                },
            },
            'required': ['id'],
        }

    def from_json(self, json_data):
        label = json_data['label'] if 'label' in json_data else ''
        return RestTestResource(json_data['id'], label)


class RestTestResourceRepository(ShrinkableResourceRepository,
                                 ExpandableResourceRepository):
    def __init__(self):
        self._type = RestTestResourceType()
        self._add_type = AddRestTestResourceType()
        resources = [
            RestTestResource('foo'),
            RestTestResource('Bar'),
        ]
        self._resources = {}
        self.add_resources(resources)

    def get_type(self):
        return self._type

    def get_add_type(self):
        return self._add_type

    def get_resource(self, resource_id):
        try:
            return self._resources[resource_id]
        except KeyError:
            raise ResourceNotFound(resource_id)

    def get_resources(self):
        return self._resources.values()

    def add_resources(self, resources: Iterable):
        for resource in resources:
            if resource.id in self._resources:
                # @todo Convert this to a proper (HTTP?) exception.
                raise RuntimeError()
            self._resources[resource.id] = resource
        return resources

    def delete_resources(self, resources: Iterable):
        for resource in resources:
            del self._resources[resource.id]
