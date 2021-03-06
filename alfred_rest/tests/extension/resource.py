from typing import Iterable

from contracts import contract

from alfred_json.type import IdentifiableDataType, OutputDataType, \
    InputDataType, UpdateInputDataType
from alfred_rest.resource import ResourceNotFound, \
    ShrinkableResourceRepository, ExpandableResourceRepository, ResourceIdType, \
    UpdateableResourceRepository


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

    @label.setter
    def label(self, label):
        self._label = label


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


class UpdateRestTestResourceType(IdentifiableDataType, InputDataType, UpdateInputDataType, OutputDataType):
    def __init__(self):
        super().__init__('rest-test-update')

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

    def update_from_json(self, json_data, instance):
        assert (instance.id == json_data['id'])
        instance.label = json_data['label']
        return instance

    def to_json(self, data):
        return {
            'id': data.id,
            'label': data.label,
        }


class RestTestResourceRepository(ShrinkableResourceRepository, ExpandableResourceRepository, UpdateableResourceRepository):
    def __init__(self):
        self._type = RestTestResourceType()
        self._add_type = AddRestTestResourceType()
        self._update_type = UpdateRestTestResourceType()
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

    def get_update_type(self):
        return self._update_type

    def get_resource(self, resource_id):
        try:
            return self._resources[resource_id]
        except KeyError:
            raise ResourceNotFound(resource_id)

    def get_resources(self, ids=None, filters=()):
        resources = self._resources.values()
        if ids is not None:
            resources = filter(lambda x: x.id in ids, resources)
        return resources

    def add_resource(self, resource):
        if resource.id in self._resources:
            # @todo Convert this to a proper (HTTP?) exception.
            raise RuntimeError()
        self._resources[resource.id] = resource

    def add_resources(self, resources: Iterable):
        for resource in resources:
            self.add_resource(resource)
        return resources

    def update_resource(self, resource):
        if resource.id not in self._resources:
            raise ResourceNotFound(self._type.name)
        self._resources[resource.id] = resource
        return resource

    def update_resources(self, resources: Iterable):
        for resource in resources:
            self.update_resource(resource)
        return resources

    def delete_resource(self, resource):
        del self._resources[resource.id]

    def delete_resources(self, resources: Iterable):
        for resource in resources:
            self.delete_resource(resource)
