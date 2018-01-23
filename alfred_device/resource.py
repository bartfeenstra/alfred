from typing import List, Iterable

from contracts import contract

from alfred_device.device import DeviceRepository, DeviceNotFound, Powerable, \
    Rgb24Colorable, Rgb24Color, Device
from alfred_http.endpoints import BadRequestError
from alfred_json.type import OutputDataType, InputDataType, \
    UpdateInputDataType
from alfred_rest.resource import ResourceNotFound, \
    UpdateableResourceRepository, ResourceType, AnyResourceType


class DeviceType(ResourceType):
    def __init__(self, data_type_name: str='device'):
        ResourceType.__init__(self, data_type_name)

    def get_json_schema(self):
        schema = super().get_json_schema()
        schema['properties']['type'] = {
            'type': 'string',
        }
        schema['required'].append('type')
        return schema

    def update_from_json(self, json_data, instance):
        assert isinstance(instance, Device)
        if instance.id != json_data['id']:
            raise BadRequestError()

    def to_json(self, data):
        assert isinstance(data, Device)
        try:
            return {
                'id': data.id,
                'type': data.type,
            }
        except AttributeError:
            raise ValueError('Resources must have an "id" property.')


class PowerableType(UpdateInputDataType, OutputDataType):
    def get_json_schema(self):
        return {
            'type': 'object',
            'properties': {
                'powered': {
                    'title': 'Whether the device is powered on or off.',
                    'type': 'boolean',
                },
            },
            'required': ['powered'],
        }

    def update_from_json(self, json_data, instance):
        assert isinstance(instance, Powerable)
        instance.powered = json_data['powered']

    def to_json(self, data):
        if isinstance(data, Powerable):
            return {
                'powered': data.powered,
            }
        return {}


class Rgb24TupleColorType(InputDataType, OutputDataType):
    def get_json_schema(self):
        return {
            'type': 'array',
            'minItems': 3,
            'maxItems': 3,
            'items': {
                'type': 'number',
                'title': 'A 24-bit RGB color, represented as a list of the three numeric color values.',
                'minimum': 0,
                'maximum': 255,
            },
        }

    def from_json(self, json_data):
        assert isinstance(json_data, List)
        assert 3 == len(json_data)
        red = json_data[0]
        green = json_data[1]
        blue = json_data[2]
        return Rgb24Color(red, green, blue)

    def to_json(self, data):
        assert isinstance(data, Rgb24Color)
        return (data.red, data.green, data.blue)


class Rgb24HexadecimalColorType(InputDataType, OutputDataType):
    def get_json_schema(self):
        return {
            'type': 'string',
            'title': 'A 24-bit RGB color, represented in hexadecimal notation.',
            'pattern': '^#[a-zA-Z0-9]{6}$',
        }

    def from_json(self, json_data):
        assert isinstance(json_data, str)
        red = int(json_data[1:3], 16)
        green = int(json_data[3:5], 16)
        blue = int(json_data[5:7], 16)
        return Rgb24Color(red, green, blue)

    def to_json(self, data):
        assert isinstance(data, Rgb24Color)
        return '#{:02X}{:02X}{:02X}'.format(data.red, data.green, data.blue)


class Rgb24ColorableType(UpdateInputDataType, OutputDataType):
    def __init__(self):
        self._color_type = Rgb24HexadecimalColorType()

    def get_json_schema(self):
        return {
            'type': 'object',
            'properties': {
                'color': self._color_type,
            },
            'required': ['color'],
        }

    def update_from_json(self, json_data, instance):
        assert isinstance(instance, Rgb24Colorable)
        instance.color = self._color_type.from_json(json_data['color'])

    def to_json(self, data):
        assert isinstance(data, Rgb24Colorable)
        return {
            'color': self._color_type.to_json(data.color),
        }


class DeviceResourceRepository(UpdateableResourceRepository):
    @contract
    def __init__(self, device_type: DeviceType, devices: DeviceRepository):
        self._devices = devices
        self._type = device_type

    def get_type(self):
        return self._type

    def get_resource(self, resource_id):
        try:
            return self._devices.get_device(resource_id)
        except DeviceNotFound:
            raise ResourceNotFound(resource_id)

    def get_resources(self, ids=None, filters=()):
        devices = self._devices.get_devices()
        if ids is not None:
            devices = filter(lambda x: x.id in ids, devices)
        # @todo Apply the filters.
        return devices

    def update_resource(self, resource):
        # Devices are updated on-the-fly, through their instances themselves,
        # to reduce lag. This usage is perhaps unusual for the resource API,
        # but it's simple and for now it works.
        return resource

    def update_resources(self, resources):
        # Devices are updated on-the-fly, through their instances themselves,
        # to reduce lag. This usage is perhaps unusual for the resource API,
        # but it's simple and for now it works.
        return resources


class NestedDeviceResourceRepository(UpdateableResourceRepository):
    def __init__(self):
        self._type = AnyResourceType(DeviceType(), 'type', lambda x: x.type)
        self._resources = []

    @contract
    def add_resources(self, resources: DeviceResourceRepository):
        self._type.add_concrete_type(resources.get_type())
        self._resources.append(resources)

    def get_type(self):
        return self._type

    def get_resource(self, resource_id):
        return self._get_resource(resource_id)[0]

    def _get_resource(self, resource_id):
        for resources in self._resources:
            try:
                return resources.get_resource(resource_id), resources
            except ResourceNotFound:
                continue
        raise ResourceNotFound(resource_id)

    def get_resources(self, ids=None, filters=()):
        return map(lambda x: x[0], self._get_resources(ids, filters))

    def _get_resources(self, ids, filters):
        retrieved_resources = []
        for resources in self._resources:
            for resource in resources.get_resources(ids, filters):
                retrieved_resources.append((resource, resources))
        # @todo (Re-)apply paging filters.
        return retrieved_resources

    def update_resource(self, resource):
        _, repo = self._get_resource(resource.id)
        return repo.update_resource(resource)

    def update_resources(self, resources: Iterable):
        updated_resources = []
        for resource in resources:
            updated_resources.append(self.update_resource(resource))
        return updated_resources
