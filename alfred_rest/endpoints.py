import abc
import json
from typing import Dict, Iterable

from contracts import contract
from flask import Request as HttpRequest

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import Endpoint, EndpointUrlBuilder, \
    EndpointRepository, \
    MessageMeta, \
    Response, SuccessResponse, SuccessResponseMeta, \
    NonConfigurableGetRequestMeta, NonConfigurableRequest, RequestMeta, \
    Request, ErrorResponse, NotFoundError, ErrorResponseMetaRepository
from alfred_rest import base64_decodes
from alfred_rest.json import Rewriter, IdentifiableDataType, ListType, \
    SchemaRepository, SchemaNotFound, Validator, InputDataType, \
    IdentifiableScalarType
from alfred_rest.resource import ResourceRepository, ResourceType, \
    ResourceIdType, ResourceNotFound


class RequestParameter:
    @contract
    def __init__(self, data_type: IdentifiableScalarType, name=None, required=True,
                 cardinality=1):
        assert isinstance(data_type, InputDataType)
        self.assert_valid_type(data_type)
        self._type = data_type
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


class RestRequestMeta(RequestMeta):
    def __init__(self, validator: Validator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validator = validator

    @contract
    def get_parameters(self) -> Iterable:
        """
        :return: Iterable[RequestParameter]
        """
        return ()

    def from_http_request(self, http_request: HttpRequest,
                          path_parameters: Dict):
        arguments = {}
        for parameter in self.get_parameters():
            name = parameter.name
            if parameter.required:
                try:
                    value = path_parameters[name]
                except KeyError:
                    raise RuntimeError('Request type "%s" (%s) requires URL path parameter "%s", which is not defined for %s.' % (
                        self.name, type(self), name, http_request.full_path))
            else:
                value = http_request.args.get(name)
            self._validator.validate(value, parameter.type)
            arguments[name] = parameter.type.from_json(value)

        return self._from_rest_request(http_request, arguments)

    @abc.abstractmethod
    def _from_rest_request(self, http_request: HttpRequest, arguments: Dict):
        pass


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


class JsonResponseMeta(SuccessResponseMeta, JsonMessageMeta):
    @contract
    def __init__(self, name: str, urls: EndpointUrlBuilder):
        super().__init__(name)
        self._urls = urls

    def to_http_response(self, response, content_type):
        http_response = super().to_http_response(response, content_type)
        # @todo Validate the JSON. But we can only do that once all children are done with this method....
        # @todo How do we do that?
        # @todo Maybe only when debug=True, though.
        # @todo Can this be moved to the parent class so we validate requests as well?
        data = self.to_json(response, content_type)
        http_response.set_data(json.dumps(data))

        return http_response

    @abc.abstractmethod
    @contract
    def to_json(self, response: Response, content_type: str):
        pass


class RestErrorResponseMeta(JsonResponseMeta):
    @contract
    def __init__(self, urls: EndpointUrlBuilder):
        super().__init__('rest-error', urls)
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


class JsonSchemaResponseMeta(JsonResponseMeta, AppAwareFactory):
    NAME = 'schema'

    @contract
    def __init__(self, urls: EndpointUrlBuilder, rewriter: Rewriter):
        super().__init__(self.NAME, urls)
        self._rewriter = rewriter

    @classmethod
    def from_app(cls, app):
        return cls(app.service('http', 'urls'),
                   app.service('rest', 'json_schema_rewriter'))

    def get_content_types(self):
        return ['application/schema+json']

    def to_json(self, response, content_type):
        assert isinstance(response, JsonSchemaResponse)
        return self._rewriter.rewrite(response.schema)

    def get_json_schema(self):
        return {
            '$ref': 'http://json-schema.org/draft-04/schema#',
        }


class JsonSchemaEndpoint(Endpoint, AppAwareFactory):
    NAME = 'schema'

    @contract
    def __init__(self, factory: Factory, endpoints: EndpointRepository,
                 urls: EndpointUrlBuilder,
                 error_response_metas: ErrorResponseMetaRepository):
        super().__init__(factory, self.NAME,
                         '/about/json/schema',
                         NonConfigurableGetRequestMeta,
                         JsonSchemaResponseMeta)
        self._endpoints = endpoints
        self._urls = urls
        self._error_response_metas = error_response_metas

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'endpoints'),
                   app.service('http', 'urls'),
                   app.service('http', 'error_response_metas'))

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
                request_meta.name, request_meta.get_json_schema() if isinstance(request_meta, JsonMessageMeta) else {})

            response_meta = endpoint.response_meta
            schema['definitions'].setdefault('response', {})
            schema['definitions']['response'].setdefault(
                response_meta.name, response_meta.get_json_schema() if isinstance(response_meta, JsonMessageMeta) else {})

        for error_response_meta in self._error_response_metas.get_metas():
            schema['definitions'].setdefault('response', {})
            schema['definitions']['response'].setdefault(
                error_response_meta.name, error_response_meta.get_json_schema() if isinstance(error_response_meta, JsonMessageMeta) else {})

        return JsonSchemaResponse(schema)


class ExternalJsonSchemaRequestMeta(RequestMeta):
    NAME = 'external-schema'

    def __init__(self):
        super().__init__(self.NAME, 'GET')

    def from_http_request(self, http_request: HttpRequest,
                          path_parameters: Dict):
        return ExternalJsonSchemaRequest(base64_decodes(path_parameters['id']))

    def get_content_types(self):
        return ['']


class ExternalJsonSchemaRequest(Request):
    @contract
    def __init__(self, schema_url: str):
        self._schema_url = schema_url

    @property
    def schema_url(self):
        return self._schema_url


class ExternalJsonSchemaEndpoint(Endpoint, AppAwareFactory):
    """
    Provides an endpoint that proxies an external JSON Schema. This circumvents
    Cross-Origin Resource Sharing (CORS) problems, by not requiring API clients
    to load external resources themselves, and allows us to fix incorrect
    headers, such as Content-Type.

    The {id} parameter is the base64-encoded URL of the schema to load.
    """

    NAME = 'external-schema'

    @contract
    def __init__(self, factory: Factory, urls: EndpointUrlBuilder,
                 schemas: SchemaRepository):
        super().__init__(factory, self.NAME,
                         '/about/json/external-schema/{id}',
                         ExternalJsonSchemaRequestMeta,
                         JsonSchemaResponseMeta)
        self._urls = urls
        self._schemas = schemas

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'urls'),
                   app.service('rest', 'json_schemas'))

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
        class ResourcesResponseMeta(JsonResponseMeta, AppAwareFactory):
            _resource_type = resource_type
            _type = ListType(resource_type)

            @contract
            def __init__(self, urls: EndpointUrlBuilder):
                super().__init__('%ss' % self._resource_type.name, urls)

            @classmethod
            def from_app(cls, app):
                return cls(app.service('http', 'urls'))

            def get_json_schema(self):
                return self._type

            def to_json(self, response, content_type):
                assert isinstance(response, ResourcesResponse)
                return self._type.to_json(response.resources)

        return ResourcesResponseMeta

    @contract
    def __init__(self, factory: Factory, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__(factory, '%ss' % resource_name,
                         '/%ss' % resource_name,
                         NonConfigurableGetRequestMeta,
                         self._build_response_meta_class(resources.get_type()))
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


class ResourceRequestMeta(RestRequestMeta, AppAwareFactory):
    @contract
    def __init__(self, validator: Validator):
        super().__init__(validator, 'resource', 'GET')

    @classmethod
    def from_app(cls, app):
        return cls(app.service('rest', 'json_validator'))

    def get_content_types(self):
        return ['']

    def _from_rest_request(self, http_request, arguments):
        return ResourceRequest(arguments['id'])

    def get_parameters(self):
        return (RequestParameter(ResourceIdType(), name='id'),)


class GetResourceEndpoint(Endpoint):
    @staticmethod
    def _build_response_meta_class(resource_type: ResourceType):
        class ResourceResponseMeta(JsonResponseMeta, AppAwareFactory):
            _type = resource_type

            @contract
            def __init__(self, urls: EndpointUrlBuilder):
                super().__init__('%s' % self._type.name, urls)

            @classmethod
            def from_app(cls, app):
                return cls(app.service('http', 'urls'))

            def get_json_schema(self):
                return self._type

            def to_json(self, response, content_type):
                assert isinstance(response, ResourceResponse)
                return self._type.to_json(response.resource)

        return ResourceResponseMeta

    @contract
    def __init__(self, factory: Factory, resources: ResourceRepository):
        resource_name = resources.get_type().name
        super().__init__(factory, resource_name, '/%ss/{id}' % resource_name,
                         ResourceRequestMeta,
                         self._build_response_meta_class(resources.get_type()))
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
    def __init__(self, resources: Iterable, factory: Factory):
        """

        :param resources: Iterable[ResourceRepository]
        :param factory:
        """
        self._resources = resources
        self._factory = factory
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
            GetResourceEndpoint(self._factory, resources),
            GetResourcesEndpoint(self._factory, resources),
        ]

        return endpoints
