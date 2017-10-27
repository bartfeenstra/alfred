import abc
from typing import Iterable

from contracts import contract

from alfred.app import Extension, ClassFactory, App
from alfred.extension import CoreExtension
from alfred_http.endpoints import Endpoint, SuccessResponse, \
    EndpointRepository, NonConfigurableRequestMeta, SuccessResponseMeta, \
    EndpointUrlBuilder, RequestMeta, Request
from alfred_http.json import Json, Validator
from alfred_http.schemas import SchemaRepository


class HttpExtensionIntegrator:
    """
    Integrates an extension with HttpExtension.

    Any class that extends Extension can extend this class as well to be picked
    up by HttpExtension automatically.
    """

    @abc.abstractmethod
    @contract
    def get_endpoints(self) -> Iterable:
        """
        Returns the endpoints this extension provides.
        :return: Iterable[Endpoint]
        """
        pass


class HttpExtension(Extension, HttpExtensionIntegrator):
    @staticmethod
    def name():
        return 'http'

    @staticmethod
    def dependencies() -> Iterable:
        return [CoreExtension]

    def _endpoint_repository(self) -> EndpointRepository:
        return ExtensionEndpointRepository(self._app)

    def _schema_repository(self) -> SchemaRepository:
        return SchemaRepository(self._app.service('core', 'endpoint_repository'),
                                self._app.service('core', 'urls'))

    def _urls(self) -> EndpointUrlBuilder:
        return EndpointUrlBuilder(self._app.service('core', 'endpoint_repository'))

    def _json_validator(self) -> Validator:
        return Validator()

    def get_services(self):
        return {
            'endpoint_repository': self._endpoint_repository,
            'schema_repository': self._schema_repository,
            'urls': self._urls,
            'json_validator': self._json_validator,
        }

    def get_endpoints(self):
        return [
            AllMessagesJsonSchemaEndpoint(
                self._app.service('schema_repository')),
            ResponseJsonSchemaEndpoint(self._app.service('schema_repository')),
        ]


class ExtensionEndpointRepository(EndpointRepository):
    def __init__(self, app: App):
        self._app = app
        self._endpoints = None

    def get_endpoint(self, endpoint_name: str):
        if self._endpoints is not None:
            return self._endpoints[endpoint_name]

        self._aggregate_endpoints()
        return self._endpoints[endpoint_name]

    def get_endpoints(self):
        if self._endpoints is not None:
            return list(self._endpoints.values())

        self._aggregate_endpoints()
        return self.get_endpoints()

    def _aggregate_endpoints(self):
        self._endpoints = {}
        for extension in self._app.extensions:
            for endpoint in extension.get_endpoints():
                self._endpoints[endpoint.name] = endpoint


class JsonSchemaResponse(SuccessResponse):
    @contract
    def __init__(self, schema: Json):
        super().__init__()
        self._has_data = True
        self._data = schema.raw


class JsonSchemaResponseMeta(SuccessResponseMeta):
    def to_http_response(self, response):
        assert isinstance(response, JsonSchemaResponse)
        return super().to_http_response(response)

    def get_json_schema(self):
        return Json.from_data({
            '$ref': 'http://json-schema.org/draft-04/schema#',
            'description': 'A JSON Schema.',
        })


class AllMessagesJsonSchemaEndpoint(Endpoint):
    NAME = 'schemas'

    @contract
    def __init__(self, schemas: SchemaRepository):
        super().__init__(self.NAME, 'GET', '/about/json/schema',
                         NonConfigurableRequestMeta(),
                         JsonSchemaResponseMeta())
        self._schemas = schemas

    def handle(self, request):
        return JsonSchemaResponse(self._schemas.get_for_all_messages())


class EndpointRequest(Request):
    @contract
    def __init__(self, endpoint_name: str):
        self._endpoint_name = endpoint_name

    @property
    @contract
    def endpoint_name(self) -> str:
        return self._endpoint_name


class EndpointRequestMeta(RequestMeta):
    """
    Defines an endpoint-specific request.
    """

    def from_http_request(self, http_request, parameters):
        return EndpointRequest(parameters['endpoint_name'])


class ResponseJsonSchemaEndpoint(Endpoint):
    NAME = 'schemas.response'

    @contract
    def __init__(self, schemas: SchemaRepository):
        super().__init__(self.NAME, 'GET',
                         '/about/json/schema/response/<endpoint_name>',
                         EndpointRequestMeta(),
                         JsonSchemaResponseMeta())
        self._schemas = schemas

    def handle(self, request):
        assert isinstance(request, EndpointRequest)
        return JsonSchemaResponse(
            self._schemas.get_for_response(request.endpoint_name))
