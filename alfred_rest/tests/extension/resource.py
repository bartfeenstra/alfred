from contracts import contract

from alfred_rest.resource import ResourceRepository, ResourceType, \
    ResourceNotFound


class RestTestResource:
    @contract
    def __init__(self, resource_id: str):
        self._id = resource_id

    @property
    def id(self):
        return self._id


class RestTestResourceType(ResourceType):
    def __init__(self):
        super().__init__({}, 'rest-test')

    def to_json(self, data):
        assert isinstance(data, RestTestResource)
        return {
            'id': data.id,
        }


class RestTestResourceRepository(ResourceRepository):
    def __init__(self):
        self._type = RestTestResourceType()
        resources = [
            RestTestResource('foo'),
            RestTestResource('Bar'),
        ]
        self._resources = {}
        for resource in resources:
            self._resources[resource.id] = resource

    def get_type(self):
        return self._type

    def get_resource(self, resource_id):
        try:
            return self._resources[resource_id]
        except KeyError:
            raise ResourceNotFound(resource_id)

    def get_resources(self):
        return self._resources.values()
