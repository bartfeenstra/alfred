import json
from typing import Dict, Iterable

from contracts import contract

from alfred.app import App
from alfred_http import base64_decodes
from alfred_http.endpoints import Endpoint, EndpointRepository, \
    SuccessResponse, NonConfigurableGetRequestType, \
    NonConfigurableRequest, RequestType, Request, ErrorResponse, NotFoundError, \
    ResponseType, PayloadType, RequestPayloadType, ResponsePayloadType, \
    RequestParameter, ErrorResponseType, EmptyResponseType
from alfred_http.http import HttpRequest, HttpResponseBuilder, HttpBody
from alfred_json.schema import SchemaNotFound
from alfred_json.type import IdentifiableDataType, ListType, \
    IdentifiableScalarType, InputDataType, OutputDataType, OutputProcessorType
from alfred_rest.resource import ResourceRepository, ResourceType, \
    ResourceIdType, ResourceNotFound, ShrinkableResourceRepository


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

    def from_http_request(self, http_request):
        # return self._data_type.from_json()
        # self._validator.validate(json_data, self.data_type.get_json_schema())
        # @todo Can we use InputProcessorType to simply turn any data structure into a response object quickly?
        # @todo
        # @todo
        pass


class JsonResponsePayloadType(JsonPayloadType, ResponsePayloadType):
    @contract
    def __init__(self, data_type: OutputDataType):
        self._data_type = data_type

    @property
    @contract
    def data_type(self) -> OutputDataType:
        return self._data_type

    def to_http_response(self, response, content_type):
        json_data = self._data_type.to_json(response)
        http_response = HttpResponseBuilder()
        http_response.body = HttpBody(json.dumps(json_data), content_type)
        return http_response


class ErrorType(IdentifiableDataType):
    def __init__(self):
        super().__init__({
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
        }, 'error')

    def to_json(self, data):
        return {
            'code': data.code,
            'title': data.title,
        }


class ErrorPayloadType(JsonResponsePayloadType):
    class ErrorResponseType(IdentifiableDataType):
        def __init__(self):
            self._data_type = ListType(ErrorType())
            super().__init__({
                'title': 'Error response',
                'type': 'object',
                'properties': {
                    'errors': self._data_type,
                },
                'required': ['errors'],
            }, 'error')

        def to_json(self, data):
            assert isinstance(data, ErrorResponse)
            return {
                'errors': self._data_type.to_json(data.errors),
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


class JsonSchemaResponse(SuccessResponse):
    @contract
    def __init__(self, schema: Dict):
        super().__init__()
        self._schema = schema

    @property
    @contract
    def schema(self) -> Dict:
        return self._schema


class JsonSchemaResponseType(ResponseType):
    def __init__(self):
        super().__init__('schema', (JsonSchemaResponsePayloadType(
            OutputProcessorType(JsonSchemaType(), lambda x: x.schema)),))


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
                        request_type.name, request_payload_type.data_type.get_json_schema())

            response_type = endpoint.response_type
            for response_payload_type in response_type.get_payload_types():
                if isinstance(response_payload_type, JsonResponsePayloadType):
                    schema['definitions'].setdefault('response', {})
                    schema['definitions']['response'].setdefault(
                        response_type.name, response_payload_type.data_type.get_json_schema())

        for error_response_payload_type in self._error_response_type.get_payload_types():
            if isinstance(error_response_payload_type, JsonResponsePayloadType):
                schema['definitions'].setdefault('response', {})
                schema['definitions']['response'].setdefault(
                    self._error_response_type.name,
                    error_response_payload_type.data_type.get_json_schema() if isinstance(
                        error_response_payload_type, JsonPayloadType) else {})

        return JsonSchemaResponse(schema)


class JsonSchemaId(IdentifiableScalarType):
    def __init__(self):
        super().__init__({
            'title': 'A JSON Schema ID.',
            'type': 'string',
            'format': 'uri',
        }, 'json-schema-id')


class ExternalJsonSchemaRequestPayloadType(RequestPayloadType):
    def get_content_types(self):
        return '',

    def from_http_request(self, http_request: HttpRequest):
        return ExternalJsonSchemaRequest(
            base64_decodes(http_request.arguments['id']))


class ExternalJsonSchemaRequestType(RequestType):
    def __init__(self):
        super().__init__('external-schema', 'GET',
                         (ExternalJsonSchemaRequestPayloadType(),))

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


class ResourcesResponse(SuccessResponse):
    @contract
    def __init__(self, resources: Iterable):
        super().__init__()
        self._resources = resources

    @property
    @contract
    def resources(self) -> Iterable:
        return self._resources


class GetResourcesEndpoint(Endpoint):
    @staticmethod
    def _build_response_type_class(resource_type: ResourceType):
        class ResourcesResponseType(ResponseType):
            _resource_type = resource_type
            _list_type = ListType(resource_type)
            _type = OutputProcessorType(_list_type, lambda x: x.resources)

            def __init__(self):
                super().__init__('%ss' % self._resource_type.name,
                                 (JsonResponsePayloadType(self._type),))

        return ResourcesResponseType

    @contract
    def __init__(self, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__('%ss' % resource_name,
                         '/%ss' % resource_name,
                         NonConfigurableGetRequestType(),
                         self._build_response_type_class(
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


class ResourceResponse(SuccessResponse):
    def __init__(self, resource):
        super().__init__()
        self._resource = resource

    @property
    def resource(self):
        return self._resource


class ResourceRequestPayloadType(RequestPayloadType):
    def get_content_types(self):
        return '',

    def from_http_request(self, http_request: HttpRequest):
        return ResourceRequest(http_request.arguments['id'])


class ResourceRequestType(RequestType):
    def __init__(self, method='GET'):
        super().__init__('resource', method, (ResourceRequestPayloadType(),))

    def get_parameters(self):
        return RequestParameter(ResourceIdType(), name='id'),


class GetResourceEndpoint(Endpoint):
    @staticmethod
    def _build_response_type_class(resource_type: ResourceType):
        class ResourceResponseType(ResponseType):
            _resource_type = resource_type
            _type = OutputProcessorType(_resource_type, lambda x: x.resource)

            def __init__(self):
                super().__init__('%s' % self._resource_type.name,
                                 (JsonResponsePayloadType(self._type),))

        return ResourceResponseType

    @contract
    def __init__(self, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__(resource_name, '/%ss/{id}' % resource_name,
                         ResourceRequestType(),
                         self._build_response_type_class(
                             resources.get_type())())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, ResourceRequest)
        try:
            return ResourceResponse(self._resources.get_resource(request.id))
        except ResourceNotFound:
            raise NotFoundError()


class DeleteResourceEndpoint(Endpoint):
    @contract
    def __init__(self, resources: ShrinkableResourceRepository):
        resource_name = resources.get_type().name
        super().__init__('%s-delete' % resource_name, '/%ss/{id}' % resource_name,
                         ResourceRequestType('DELETE'),
                         EmptyResponseType())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, ResourceRequest)
        try:
            resource = self._resources.get_resource(request.id)
        except ResourceNotFound:
            raise NotFoundError()
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
        if isinstance(resources, ShrinkableResourceRepository):
            endpoints.append(DeleteResourceEndpoint(resources))

        return endpoints
