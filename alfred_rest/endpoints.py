import abc
import json
from typing import Dict, Iterable

from contracts import contract

from alfred.app import App
from alfred_http.endpoints import Endpoint, EndpointRepository, \
    MessageMeta, \
    Response, SuccessResponse, NonConfigurableGetRequestMeta, \
    NonConfigurableRequest, RequestMeta, \
    Request, ErrorResponse, NotFoundError, ResponseMeta
from alfred_http.http import HttpRequest, HttpBody
from alfred_rest import base64_decodes
from alfred_rest.json import IdentifiableDataType, ListType, \
    SchemaNotFound, InputDataType, \
    IdentifiableScalarType
from alfred_rest.resource import ResourceRepository, ResourceType, \
    ResourceIdType, ResourceNotFound


class RequestParameter:
    @contract
    def __init__(self, data_type: IdentifiableScalarType, name=None,
                 required=True,
                 cardinality=1):
        assert isinstance(data_type, InputDataType)
        self.assert_valid_type(data_type)
        self._type = data_type
        assert cardinality > 0
        # Required parameters appear in paths, and we do not support multiple
        #  values there.
        if required:
            assert 1 == cardinality
        self._required = required
        self._cardinality = cardinality
        self._name = name

    @property
    @contract
    def name(self) -> str:
        return self._name if self._name is not None else self.type.name

    @property
    @contract
    def required(self) -> bool:
        return self._required

    @property
    @contract
    def cardinality(self) -> int:
        return self._cardinality

    @property
    @contract
    def type(self) -> IdentifiableScalarType:
        return self._type

    @staticmethod
    @contract
    def assert_valid_type(schema: Dict):
        if 'enum' in schema:
            for value in schema['enum']:
                assert isinstance(value,
                                  (str, int, float, bool)) or value is None
        elif 'type' in schema:
            assert schema['type'] in ('string', 'number', 'boolean')


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
                    'title': 'The human-readable error title.',
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
        }, 'error', 'response')

    def to_json(self, data):
        assert isinstance(data, ErrorResponse)
        return {
            'errors': self._data_type.to_json(data.errors),
        }


class JsonMessageMeta(MessageMeta):
    def get_content_types(self):
        return ['application/json']

    @abc.abstractmethod
    @contract
    def get_json_schema(self) -> Dict:
        pass


class JsonRequestMeta(RequestMeta, JsonMessageMeta):
    @RequestMeta.validate_http_request.register()
    def _validate_http_request_body(self, http_request):
        validator = App.current.service('rest', 'json_validator')
        validator.validate(json.loads(http_request.body.content), self.get_json_schema())


class JsonResponseMeta(ResponseMeta, JsonMessageMeta):
    @ResponseMeta._build_http_response.register()
    def _build_http_response_body(self, response, content_type, http_response):
        data = self.to_json(response, content_type)
        http_response.body = HttpBody(json.dumps(data), content_type)

    @ResponseMeta._build_http_response.register(weight=999)
    def _build_http_response_body_validation(self, response, content_type, http_response):
        validator = App.current.service('rest', 'json_validator')
        validator.validate(json.loads(http_response.body.content), self.get_json_schema())

    @abc.abstractmethod
    @contract
    def to_json(self, response: Response, content_type: str):
        pass


class RestErrorResponseMeta(JsonResponseMeta):
    def __init__(self):
        super().__init__('rest-error')
        self._data_type = ErrorResponseType()

    def to_json(self, response, content_type):
        return self._data_type.to_json(response)

    def get_json_schema(self):
        return self._data_type


class JsonSchemaResponse(SuccessResponse):
    @contract
    def __init__(self, schema: Dict):
        super().__init__()
        self._schema = schema

    @property
    @contract
    def schema(self) -> Dict:
        return self._schema


class JsonSchemaResponseMeta(JsonResponseMeta):
    NAME = 'schema'

    def __init__(self):
        super().__init__(self.NAME)
        self._rewriter = App.current.service('rest', 'json_schema_rewriter')

    def get_content_types(self):
        return ['application/schema+json']

    def to_json(self, response, content_type):
        assert isinstance(response, JsonSchemaResponse)
        return self._rewriter.rewrite(response.schema)

    def get_json_schema(self):
        return {
            '$ref': 'http://json-schema.org/draft-04/schema#',
        }


class JsonSchemaEndpoint(Endpoint):
    NAME = 'schema'

    def __init__(self):
        super().__init__(self.NAME,
                         '/about/json/schema',
                         NonConfigurableGetRequestMeta(),
                         JsonSchemaResponseMeta())
        self._endpoints = App.current.service('http', 'endpoints')
        self._urls = App.current.service('http', 'urls')
        self._error_response_metas = App.current.service(
            'http', 'error_response_metas')

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
            request_meta = endpoint.request_meta
            schema['definitions'].setdefault('request', {})
            schema['definitions']['request'].setdefault(
                request_meta.name,
                request_meta.get_json_schema() if isinstance(request_meta,
                                                             JsonMessageMeta) else {})

            response_meta = endpoint.response_meta
            schema['definitions'].setdefault('response', {})
            schema['definitions']['response'].setdefault(
                response_meta.name,
                response_meta.get_json_schema() if isinstance(response_meta,
                                                              JsonMessageMeta) else {})

        for error_response_meta in self._error_response_metas.get_metas():
            schema['definitions'].setdefault('response', {})
            schema['definitions']['response'].setdefault(
                error_response_meta.name,
                error_response_meta.get_json_schema() if isinstance(
                    error_response_meta, JsonMessageMeta) else {})

        return JsonSchemaResponse(schema)


class JsonSchemaId(IdentifiableScalarType):
    def __init__(self):
        super().__init__({
            'title': 'A JSON Schema ID.',
            'type': 'string',
            'format': 'uri',
        }, 'json-schema-id')


class ExternalJsonSchemaRequestMeta(RequestMeta):
    NAME = 'external-schema'

    def __init__(self):
        super().__init__(self.NAME, 'GET')

    def from_http_request(self, http_request: HttpRequest):
        return ExternalJsonSchemaRequest(
            base64_decodes(http_request.arguments['id']))

    def get_content_types(self):
        return ['']

    def get_parameters(self):
        return (RequestParameter(JsonSchemaId(), name='id'),)


class ExternalJsonSchemaRequest(Request):
    @contract
    def __init__(self, schema_url: str):
        self._schema_url = schema_url

    @property
    def schema_url(self):
        return self._schema_url


class ExternalJsonSchemaEndpoint(Endpoint):
    """
    Provides an endpoint that proxies an external JSON Schema. This circumvents
    Cross-Origin Resource Sharing (CORS) problems, by not requiring API clients
    to load external resources themselves, and allows us to fix incorrect
    headers, such as Content-Type.

    The {id} parameter is the base64-encoded URL of the schema to load.
    """

    NAME = 'external-schema'

    def __init__(self):
        super().__init__(self.NAME,
                         '/about/json/external-schema/{id}',
                         ExternalJsonSchemaRequestMeta(),
                         JsonSchemaResponseMeta())
        self._urls = App.current.service('http', 'urls')
        self._schemas = App.current.service('rest', 'json_schemas')

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
    def _build_response_meta_class(resource_type: ResourceType):
        class ResourcesResponseMeta(JsonResponseMeta):
            _resource_type = resource_type
            _type = ListType(resource_type)

            def __init__(self):
                super().__init__('%ss' % self._resource_type.name)

            def get_json_schema(self):
                return self._type

            def to_json(self, response, content_type):
                assert isinstance(response, ResourcesResponse)
                return self._type.to_json(response.resources)

        return ResourcesResponseMeta

    @contract
    def __init__(self, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__('%ss' % resource_name,
                         '/%ss' % resource_name,
                         NonConfigurableGetRequestMeta(),
                         self._build_response_meta_class(
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


class ResourceRequestMeta(RequestMeta):
    def __init__(self):
        super().__init__('resource', 'GET')

    def get_content_types(self):
        return ['']

    def from_http_request(self, http_request):
        return ResourceRequest(http_request.arguments['id'])

    def get_parameters(self):
        return (RequestParameter(ResourceIdType(), name='id'),)


class GetResourceEndpoint(Endpoint):
    @staticmethod
    def _build_response_meta_class(resource_type: ResourceType):
        class ResourceResponseMeta(JsonResponseMeta):
            _type = resource_type

            def __init__(self):
                super().__init__('%s' % self._type.name)

            def get_json_schema(self):
                return self._type

            def to_json(self, response, content_type):
                assert isinstance(response, ResourceResponse)
                return self._type.to_json(response.resource)

        return ResourceResponseMeta

    @contract
    def __init__(self, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__(resource_name, '/%ss/{id}' % resource_name,
                         ResourceRequestMeta(),
                         self._build_response_meta_class(
                             resources.get_type())())
        self._resources = resources

    def handle(self, request: Request):
        assert isinstance(request, ResourceRequest)
        try:
            return ResourceResponse(self._resources.get_resource(request.id))
        except ResourceNotFound:
            raise NotFoundError()


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

        return endpoints
