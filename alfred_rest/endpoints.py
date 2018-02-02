import json
from json import JSONDecodeError
from typing import Dict, Iterable, Union

from contracts import contract
from jsonpatch import JsonPatch
from jsonschema import ValidationError

from alfred.app import App
from alfred_http import base64_decodes
from alfred_http.endpoints import Endpoint, EndpointRepository, \
    SuccessResponse, NonConfigurableGetRequestType, \
    NonConfigurableRequest, RequestType, Request, NotFoundError, \
    ResponseType, PayloadType, RequestPayloadType, ResponsePayloadType, \
    RequestParameter, ErrorResponseType, EmptyResponseType, BadRequestError, \
    PayloadedMessage, Error
from alfred_http.http import HttpRequest, HttpBody
from alfred_json import RESOURCE_PATH
from alfred_json.schema import SchemaNotFound
from alfred_json.type import IdentifiableDataType, ListType, \
    IdentifiableScalarType, InputDataType, OutputDataType
from alfred_rest.resource import ResourceRepository, ResourceIdType, \
    ResourceNotFound, ShrinkableResourceRepository, \
    ExpandableResourceRepository, UpdateableResourceRepository


class JsonPayloadType(PayloadType):
    def get_content_types(self):
        return ['application/json']


class JsonRequestPayloadType(JsonPayloadType, RequestPayloadType):
    @contract
    def __init__(self, data_type: InputDataType):
        self._data_type = data_type
        self._validator = App.current.service('json', 'validator')

    @property
    @contract
    def data_type(self) -> InputDataType:
        return self._data_type

    def from_http_request_body(self, http_request_body):
        try:
            json_data = json.loads(http_request_body.content)
        except JSONDecodeError as e:
            raise BadRequestError(description=str(e))
        try:
            self._validator.validate(
                json_data, self._data_type.get_json_schema())
        except ValidationError as e:
            raise BadRequestError(description=str(e))
        return self._data_type.from_json(json_data)


class JsonResponsePayloadType(JsonPayloadType, ResponsePayloadType):
    @contract
    def __init__(self, data_type: OutputDataType):
        self._data_type = data_type

    @property
    @contract
    def data_type(self) -> OutputDataType:
        return self._data_type

    def to_http_response_body(self, payload, content_type):
        json_data = self._data_type.to_json(payload)
        return HttpBody(json.dumps(json_data), content_type)


class ErrorType(IdentifiableDataType, OutputDataType):
    def __init__(self):
        super().__init__('error')

    def get_json_schema(self):
        return {
            'title': 'An API error',
            'type': 'object',
            'properties': {
                'code': {
                    'title': 'The machine-readable error code.',
                    'type': 'string',
                },
                'title': {
                    'title': 'The human-readable, generic title of this type of error.',
                    'type': 'string',
                },
                'description': {
                    'title': 'The human-readable description of this particular occurrence of the error.',
                    'type': 'string',
                },
            },
            'required': ['code', 'title'],
        }

    def to_json(self, data):
        assert isinstance(data, Error)
        json_data = {
            'code': data.code,
            'title': data.title,
        }
        if data.description:
            json_data['description'] = data.description
        return json_data


class ErrorPayloadType(JsonResponsePayloadType):
    class ErrorResponseType(IdentifiableDataType, OutputDataType):
        def __init__(self):
            self._data_type = ListType(ErrorType())
            super().__init__('error')

        def get_json_schema(self):
            return {
                'title': 'Error response',
                'type': 'object',
                'properties': {
                    'errors': self._data_type,
                },
                'required': ['errors'],
            }

        def to_json(self, data):
            return {
                'errors': self._data_type.to_json(data),
            }

    def __init__(self):
        super().__init__(self.ErrorResponseType())


class JsonSchemaType(InputDataType, OutputDataType):
    def get_json_schema(self):
        return {
            '$ref': 'http://json-schema.org/draft-04/schema#',
        }

    def from_json(self, json_data):
        assert isinstance(json_data, Dict)
        return json_data

    def to_json(self, data):
        assert isinstance(data, Dict)
        rewriter = App.current.service('json', 'schema_rewriter')
        data = rewriter.rewrite(data)
        return data


class JsonSchemaResponsePayloadType(JsonResponsePayloadType):
    def get_content_types(self):
        return ['application/schema+json']


class JsonSchemaResponse(SuccessResponse, PayloadedMessage):
    @contract
    def __init__(self, schema: Dict):
        super().__init__()
        self._schema = schema

    @property
    def payload(self):
        return self._schema


class JsonSchemaResponseType(ResponseType):
    def __init__(self):
        super().__init__('schema',
                         (JsonSchemaResponsePayloadType(JsonSchemaType()),))


class JsonSchemaEndpoint(Endpoint):
    def __init__(self):
        super().__init__('schema', '/about/json/schema',
                         NonConfigurableGetRequestType(),
                         JsonSchemaResponseType())
        self._endpoints = App.current.service('http', 'endpoints')
        self._urls = App.current.service('http', 'urls')
        self._error_response_type = ErrorResponseType()

    def handle(self, request):
        assert isinstance(request, NonConfigurableRequest)

        schema = {
            'id': self._urls.build(self.name),
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'description': 'The Alfred JSON Schema. Any data matches subschemas under #/definitions only.',
            # Prevent most values from validating against the top-level schema.
            'enum': [None],
            'definitions': {},
        }

        for endpoint in self._endpoints.get_endpoints():
            request_type = endpoint.request_type
            for request_payload_type in request_type.get_payload_types():
                if isinstance(request_payload_type, JsonRequestPayloadType):
                    schema['definitions'].setdefault('request', {})
                    schema['definitions']['request'].setdefault(
                        request_type.name,
                        request_payload_type.data_type.get_json_schema())

            response_type = endpoint.response_type
            for response_payload_type in response_type.get_payload_types():
                if isinstance(response_payload_type, JsonResponsePayloadType):
                    schema['definitions'].setdefault('response', {})
                    schema['definitions']['response'].setdefault(
                        response_type.name,
                        response_payload_type.data_type.get_json_schema())

        for error_response_payload_type in self._error_response_type.get_payload_types():
            if isinstance(error_response_payload_type,
                          JsonResponsePayloadType):
                schema['definitions'].setdefault('response', {})
                schema['definitions']['response'].setdefault(
                    self._error_response_type.name,
                    error_response_payload_type.data_type.get_json_schema() if isinstance(
                        error_response_payload_type, JsonPayloadType) else {})

        return JsonSchemaResponse(schema)


class JsonSchemaId(IdentifiableScalarType):
    def __init__(self):
        super().__init__('json-schema-id')

    def get_json_schema(self):
        return {
            'title': 'A JSON Schema ID.',
            'type': 'string',
            'format': 'uri',
        }


class ExternalJsonSchemaRequestType(RequestType):
    def __init__(self):
        super().__init__('external-schema', 'GET')

    def from_http_request(self, http_request: HttpRequest):
        return ExternalJsonSchemaRequest(
            base64_decodes(http_request.arguments['id']))

    def get_parameters(self):
        return RequestParameter(JsonSchemaId(), name='id'),


class ExternalJsonSchemaRequest(Request):
    @contract
    def __init__(self, schema_url: str):
        self._schema_url = schema_url

    @property
    def schema_url(self):
        return self._schema_url


class ExternalJsonSchemaEndpoint(Endpoint):
    """
    Provides an endpoint that serves an external JSON Schema. This circumvents
    Cross-Origin Resource Sharing (CORS) problems, by not requiring API clients
    to load external resources themselves, and allows us to fix incorrect
    headers, such as Content-Type.

    The {id} parameter is the base64-encoded URL of the schema to load.
    """

    def __init__(self):
        super().__init__('external-schema', '/about/json/external-schema/{id}',
                         ExternalJsonSchemaRequestType(),
                         JsonSchemaResponseType())
        self._urls = App.current.service('http', 'urls')
        self._schemas = App.current.service('json', 'schemas')

    def handle(self, request):
        assert isinstance(request, ExternalJsonSchemaRequest)
        schema_url = request.schema_url
        try:
            schema = self._schemas.get_schema(schema_url)
            return JsonSchemaResponse(schema)
        except SchemaNotFound:
            raise NotFoundError()


class ResourcesResponse(SuccessResponse, PayloadedMessage):
    @contract
    def __init__(self, resources: Iterable):
        super().__init__()
        self._resources = resources

    @property
    def payload(self):
        return self._resources


def build_resources_response_type_class(
        resource_type: Union[OutputDataType, IdentifiableDataType]):
    assert isinstance(resource_type, OutputDataType)
    assert isinstance(resource_type, IdentifiableDataType)

    class ResourcesResponseType(ResponseType):
        _resource_type = resource_type
        _type = ListType(resource_type)

        def __init__(self):
            super().__init__('%ss' % self._resource_type.name,
                             (JsonResponsePayloadType(self._type),))

    return ResourcesResponseType


class GetResourcesEndpoint(Endpoint):
    @contract
    def __init__(self, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__('%ss' % resource_name,
                         '/%ss' % resource_name,
                         NonConfigurableGetRequestType(),
                         build_resources_response_type_class(
                             resources.get_type())())
        self._resources = resources

    def handle(self, request: Request):
        return ResourcesResponse(self._resources.get_resources())


class ResourceRequest(Request):
    @contract
    def __init__(self, resource_id: str):
        self._id = resource_id

    @property
    @contract
    def id(self) -> str:
        return self._id


class ResourceResponse(SuccessResponse, PayloadedMessage):
    def __init__(self, resource):
        super().__init__()
        assert resource is not None
        self._resource = resource

    @property
    def payload(self):
        return self._resource


class ResourceRequestType(RequestType):
    def __init__(self, method='GET', payload_types=()):
        super().__init__('resource', method, payload_types)

    def get_parameters(self):
        return RequestParameter(ResourceIdType(), name='id'),

    def from_http_request(self, http_request: HttpRequest):
        return ResourceRequest(http_request.arguments['id'])


def build_resource_response_type_class(
        resource_type: Union[OutputDataType, IdentifiableDataType]):
    assert isinstance(resource_type, OutputDataType)
    assert isinstance(resource_type, IdentifiableDataType)

    class ResourceResponseType(ResponseType):
        _resource_type = resource_type

        def __init__(self):
            super().__init__('%s' % self._resource_type.name,
                             (JsonResponsePayloadType(self._resource_type),))

    return ResourceResponseType


class GetResourceEndpoint(Endpoint):
    @contract
    def __init__(self, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__(resource_name, '/%ss/{id}' % resource_name,
                         ResourceRequestType(),
                         build_resource_response_type_class(
                             resources.get_type())())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, ResourceRequest)
        try:
            return ResourceResponse(self._resources.get_resource(request.id))
        except ResourceNotFound:
            raise NotFoundError()


def build_add_resource_request_type_class(
        resource_type: Union[InputDataType, IdentifiableDataType]):
    assert isinstance(resource_type, InputDataType)
    assert isinstance(resource_type, IdentifiableDataType)

    class AddResourceRequestType(RequestType):
        _type = resource_type

        def __init__(self):
            super().__init__('%s' % self._type.name, 'POST',
                             (JsonRequestPayloadType(self._type),))

        def from_http_request(self, http_request):
            return AddResourceRequest(
                self._from_http_request_payload(http_request.body))

    return AddResourceRequestType


class AddResourceRequest(Request, PayloadedMessage):
    def __init__(self, resource):
        self._resource = resource

    @property
    def payload(self):
        return self._resource


class AddResourceEndpoint(Endpoint):
    @contract
    def __init__(self, resources: ExpandableResourceRepository):
        resource_name = resources.get_type().name
        super().__init__('%s-add' % resource_name, '/%ss' % resource_name,
                         build_add_resource_request_type_class(
                             resources.get_add_type())(),
                         build_resource_response_type_class(
                             resources.get_type())())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, AddResourceRequest)
        resource = request.payload
        # @todo How to handle validation?
        resources = self._resources.add_resources((resource,))
        return ResourceResponse(list(resources)[0])


def build_replace_resource_request_type_class(
        resource_type: Union[InputDataType, IdentifiableDataType]):
    assert isinstance(resource_type, InputDataType)
    assert isinstance(resource_type, IdentifiableDataType)

    class ReplaceResourceRequestType(RequestType):
        _resource_type = resource_type

        def __init__(self):
            super().__init__('%s' % self._resource_type.name, 'PUT',
                             (JsonRequestPayloadType(self._resource_type),))

        def from_http_request(self, http_request: HttpRequest):
            return ReplaceResourceRequest(http_request.arguments['id'],
                                          self._from_http_request_payload(
                                              http_request.body))

        def get_parameters(self):
            return RequestParameter(ResourceIdType(), name='id'),

    return ReplaceResourceRequestType


class ReplaceResourceRequest(Request, PayloadedMessage):
    @contract
    def __init__(self, resource_id: str, resource):
        assert resource is not None
        self._resource_id = resource_id
        self._resource = resource

    @property
    def resource_id(self) -> str:
        return self._resource_id

    @property
    def payload(self):
        return self._resource


class ReplaceResourceEndpoint(Endpoint):
    @contract
    def __init__(self, resources: UpdateableResourceRepository):
        resource_name = resources.get_type().name
        super().__init__('%s-replace' % resource_name,
                         '/%ss/{id}' % resource_name,
                         build_replace_resource_request_type_class(
                             resources.get_update_type())(),
                         build_resource_response_type_class(
                             resources.get_type())())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, ReplaceResourceRequest)
        resource = request.payload
        # @todo How to handle validation?
        try:
            resources = self._resources.update_resources((resource,))
        except ResourceNotFound as e:
            raise NotFoundError(description=str(e))
        return ResourceResponse(list(resources)[0])


class JsonPatchPathType(IdentifiableDataType):
    def __init__(self):
        super().__init__('json-patch-path')

    def get_json_schema(self):
        with open(RESOURCE_PATH + '/schemas/json-patch.json') as f:
            return json.load(f)['definitions']['path']


class JsonPatchOperationType(IdentifiableDataType):
    def __init__(self):
        super().__init__('json-patch-operation')

    def get_json_schema(self):
        with open(RESOURCE_PATH + '/schemas/json-patch.json') as f:
            schema = json.load(f)['definitions']['operation']
            schema['allOf'] = [JsonPatchPathType()]
            return schema


class JsonPatchType(InputDataType, OutputDataType, IdentifiableDataType):
    def __init__(self):
        super().__init__('json-patch')

    def get_json_schema(self):
        with open(RESOURCE_PATH + '/schemas/json-patch.json') as f:
            schema = json.load(f)
            del schema['definitions']
            schema['items'] = JsonPatchOperationType()
            return schema

    def from_json(self, json_data):
        return JsonPatch(json_data)

    def to_json(self, data):
        assert isinstance(data, JsonPatch)
        return data.patch


class JsonPatchRequestPayloadType(JsonRequestPayloadType):
    """
    An RFC 6902 JSON Patch request payload type.
    """

    def __init__(self):
        super().__init__(JsonPatchType())

    def get_content_types(self):
        return ['application/json-patch+json']


class AlterResourceRequest(Request, PayloadedMessage):
    @contract
    def __init__(self, resource_id: str, patch: JsonPatch):
        self._resource_id = resource_id
        self._patch = patch

    @property
    @contract
    def resource_id(self) -> str:
        return self._resource_id

    @property
    def payload(self):
        return self._patch


class AlterResourceRequestType(RequestType):
    @contract
    def __init__(self, resource_type_name: str):
        super().__init__('%s-alter' % resource_type_name, 'PATCH',
                         (JsonPatchRequestPayloadType(),))

    def get_parameters(self):
        return RequestParameter(ResourceIdType(), name='id'),

    def from_http_request(self, http_request: HttpRequest):
        return AlterResourceRequest(http_request.arguments['id'],
                                    self._from_http_request_payload(
                                        http_request.body))


class AlterResourceEndpoint(Endpoint):
    @contract
    def __init__(self, resources: UpdateableResourceRepository):
        resource_type = resources.get_type()
        # We can only patch resources automatically if the update data type
        # can serialize as well as deserialize.
        assert isinstance(resource_type, OutputDataType)
        resource_name = resource_type.name
        super().__init__('%s-alter' % resource_name,
                         '/%ss/{id}' % resource_name,
                         AlterResourceRequestType(resource_type.name),
                         build_resource_response_type_class(
                             resource_type)())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, AlterResourceRequest)
        resource_type = self._resources.get_update_type()
        resource_id = request.resource_id
        patch = request.payload
        try:
            resource = self._resources.get_resource(resource_id)
        except ResourceNotFound:
            raise NotFoundError()
        resource_data = resource_type.to_json(resource)
        resource_data = patch.apply(resource_data)
        resource = resource_type.update_from_json(resource_data, resource)
        # @todo How to handle validation?
        try:
            updated_resource = self._resources.update_resource(resource)
        except ResourceNotFound as e:
            raise NotFoundError(description=str(e))
        return ResourceResponse(updated_resource)


class AlterResourcesRequest(Request, PayloadedMessage):
    @contract
    def __init__(self, patch: JsonPatch):
        self._patch = patch

    @property
    def payload(self):
        return self._patch


class AlterResourcesRequestType(RequestType):
    @contract
    def __init__(self, resource_type_name: str):
        super().__init__('%ss-alter' % resource_type_name, 'PATCH',
                         (JsonPatchRequestPayloadType(),))

    def from_http_request(self, http_request: HttpRequest):
        return AlterResourcesRequest(
            self._from_http_request_payload(http_request.body))


class AlterResourcesEndpoint(Endpoint):
    @contract
    def __init__(self, resources: UpdateableResourceRepository):
        resource_type = resources.get_type()
        # We can only patch resources automatically if the update data type
        # can serialize as well as deserialize.
        assert isinstance(resource_type, OutputDataType)
        resource_name = resource_type.name
        super().__init__('%ss-alter' % resource_name,
                         '/%ss' % resource_name,
                         AlterResourcesRequestType(resource_type.name),
                         build_resources_response_type_class(
                             resource_type)())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, AlterResourcesRequest)
        resource_type = self._resources.get_update_type()
        patch = request.payload
        resources = self._resources.get_resources()
        updated_resources = []
        for resource in resources:
            resource_data = resource_type.to_json(resource)
            resource_data = patch.apply(resource_data)
            updated_resources.append(resource_type.from_json(resource_data))
        # @todo How to handle validation?
        updated_resources = self._resources.update_resources(updated_resources)
        return ResourcesResponse(updated_resources)


class DeleteResourceEndpoint(Endpoint):
    @contract
    def __init__(self, resources: ShrinkableResourceRepository):
        resource_name = resources.get_type().name
        super().__init__('%s-delete' % resource_name,
                         '/%ss/{id}' % resource_name,
                         ResourceRequestType('DELETE'),
                         EmptyResponseType())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, ResourceRequest)
        try:
            resource = self._resources.get_resource(request.id)
        except ResourceNotFound:
            return SuccessResponse()
        self._resources.delete_resources((resource,))
        return SuccessResponse()


class ResourceEndpointRepository(EndpointRepository):
    """
    Provides endpoints for resource types.
    """

    @contract
    def __init__(self, resources: Iterable):
        """

        :param resources: Iterable[ResourceRepository]
        """
        self._resources = resources
        self._endpoints = None

    def get_endpoints(self):
        if self._endpoints is None:
            self._aggregate_endpoints()

        return self._endpoints

    def _aggregate_endpoints(self):
        self._endpoints = []
        for resources in self._resources:
            self._endpoints += self._aggregate_resource_endpoints(resources)

    @contract
    def _aggregate_resource_endpoints(self, resources: ResourceRepository):
        endpoints = [
            GetResourceEndpoint(resources),
            GetResourcesEndpoint(resources),
        ]
        if isinstance(resources, ExpandableResourceRepository):
            endpoints.append(AddResourceEndpoint(resources))
        if isinstance(resources, UpdateableResourceRepository):
            endpoints.append(ReplaceResourceEndpoint(resources))
            if isinstance(resources.get_update_type(), OutputDataType):
                endpoints.append(AlterResourceEndpoint(resources))
                endpoints.append(AlterResourcesEndpoint(resources))
        if isinstance(resources, ShrinkableResourceRepository):
            endpoints.append(DeleteResourceEndpoint(resources))

        return endpoints
