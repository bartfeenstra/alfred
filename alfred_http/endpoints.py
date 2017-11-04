import json
from copy import copy
from typing import Iterable, Optional, Dict

from contracts import contract, ContractsMeta, with_metaclass
from flask import Request as HttpRequest, Response as HttpResponse, url_for

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.json import Json


class Error(Exception):
    @contract
    def __init__(self, code: str):
        self._code = code

    @property
    def code(self):
        return self._code


class MessageMeta(AppAwareFactory,
                  with_metaclass(ContractsMeta)):
    def get_json_schema(self) -> Optional[Json]:
        return None


class Message(with_metaclass(ContractsMeta)):
    pass


class Request(Message):
    pass


class RequestMeta(MessageMeta):
    @contract
    def from_http_request(self, http_request: HttpRequest,
                          parameters: Dict) -> Request:
        pass


class NonConfigurableRequest(Request):
    pass


class NonConfigurableRequestMeta(RequestMeta):
    """
    Defines a non-configurable request.
    """

    def from_http_request(self, http_request, parameters):
        return NonConfigurableRequest()


class Response(Message):
    pass


class ResponseMeta(MessageMeta, AppAwareFactory):
    def __init__(self, schemas):
        self._schemas = schemas

    @classmethod
    def from_app(cls, app):
        print()
        print(app.service('http', 'schemas'))
        return cls(app.service('http', 'schemas'))

    @contract
    def to_http_response(self, response: Response) -> HttpResponse:
        http_response = HttpResponse(content_type='application/vnd.api+json')
        if self._has_body(response):
            body = self._get_body(response)
            print(response)
            assert body is None or isinstance(body, Dict)
            if body is not None:
                # @todo  PROBLEM:  We're rendering the response, but to get the schema, we'll need the ENDPOINT name... Requests and responses can be used by multiple endpoints...
                body['$schema'] = self._schemas.get_url_for_response(
                    'schemas.response')
            http_response.set_data(json.dumps(body))
        return http_response

    @contract
    def _has_body(self, response: Response) -> bool:
        return False

    def _get_body(self, response: Response) -> Optional[Dict]:
        return None


class SuccessResponse(Response):
    def __init__(self):
        self._has_data = False
        self._data = None

    @contract
    def has_data(self) -> bool:
        return self._has_data

    def get_data(self):
        if not self.has_data():
            raise LookupError('This response has no data yet.')
        return self._data


class SuccessResponseMeta(ResponseMeta):
    def to_http_response(self, response):
        assert isinstance(response, SuccessResponse)
        http_response = super().to_http_response(response)
        http_response.status_code = 200
        return http_response

    @contract
    def _has_body(self, response: Response) -> bool:
        assert isinstance(response, SuccessResponse)
        return self.get_json_schema() is not None and response.has_data()

    def _get_body(self, response: Response) -> Optional[Dict]:
        assert isinstance(response, SuccessResponse)
        if not self._has_body(response):
            raise RuntimeError('This response has no body.')
        return response.get_data()


class ErrorResponse(Response):
    def __init__(self):
        self._errors = []

    def with_error(self, error: Error):
        message = copy(self)
        message._errors.append(error)
        return message

    @property
    def errors(self) -> Iterable:
        return self._errors


class Endpoint(with_metaclass(ContractsMeta)):
    _allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

    @contract
    def __init__(self, factory: Factory, name: str, method: str, path: str,
                 request_meta_class: type,
                 response_meta_class: type):
        assert issubclass(request_meta_class, RequestMeta)
        assert issubclass(response_meta_class, ResponseMeta)
        self._name = name
        method = method.upper()
        assert method in self._allowed_methods
        self._method = method
        self._path = path
        self._request_meta = factory.defer(request_meta_class)
        self._response_meta = factory.defer(response_meta_class)

    @property
    def name(self) -> str:
        return self._name

    @property
    def method(self) -> str:
        return self._method

    @property
    def path(self) -> str:
        return self._path

    @property
    @contract
    def request_meta(self) -> RequestMeta:
        # @todo Find out why LazyValue.__get__() does not work here.
        return self._request_meta.value

    @property
    @contract
    def response_meta(self) -> ResponseMeta:
        # @todo Find out why LazyValue.__get__() does not work here.
        return self._response_meta.value

    @contract
    def handle(self, request: Request) -> Response:
        pass


class EndpointRepository(with_metaclass(ContractsMeta)):
    @contract
    def get_endpoint(self, endpoint_name: str) -> Endpoint:
        pass

    @contract
    def get_endpoints(self) -> Iterable:
        pass


class EndpointUrlBuilder:
    @contract
    def __init__(self, endpoints: EndpointRepository):
        self._endpoints = endpoints

    def build(self, endpoint_name: str, parameters: Optional[Dict]):
        endpoint = self._endpoints.get_endpoint(endpoint_name)
        if parameters is None:
            parameters = {}
        return url_for(endpoint.path, **parameters)


class EndpointFactoryRepository(EndpointRepository):
    @contract
    def __init__(self, factory: Factory, endpoint_classes: Iterable):
        self._factory = factory
        self._endpoint_classes = endpoint_classes
        self._endpoints = None

    def get_endpoint(self, endpoint_name: str):
        if self._endpoints is None:
            self._aggregate_endpoints()
        return self._endpoints[endpoint_name]

    def get_endpoints(self):
        if self._endpoints is None:
            self._aggregate_endpoints()
        return self._endpoints.values()

    def _aggregate_endpoints(self):
        self._endpoints = {}
        for endpoint_class in self._endpoint_classes:
            endpoint = self._factory.new(endpoint_class)
            self._endpoints[endpoint.name] = endpoint


class NestedEndpointRepository(EndpointRepository):
    def __init__(self):
        self._endpoints = None
        self._endpoint_repositories = []

    @contract
    def add_endpoints(self, endpoints: EndpointRepository):
        self._endpoint_repositories.append(endpoints)

    def get_endpoint(self, endpoint_name: str):
        if self._endpoints is None:
            self._aggregate_endpoints()
        return self._endpoints[endpoint_name]

    def get_endpoints(self):
        if self._endpoints is None:
            self._aggregate_endpoints()
        return self._endpoints.values()

    def _aggregate_endpoints(self):
        self._endpoints = {}
        for endpoints in self._endpoint_repositories:
            for endpoint in endpoints.get_endpoints():
                self._endpoints[endpoint.name] = endpoint


class JsonSchemaResponse(SuccessResponse):
    @contract
    def __init__(self, schema: Json):
        super().__init__()
        self._has_data = True
        self._data = schema.data


class JsonSchemaResponseMeta(SuccessResponseMeta):
    def to_http_response(self, response):
        assert isinstance(response, JsonSchemaResponse)
        return super().to_http_response(response)

    def get_json_schema(self):
        return Json.from_data({
            '$ref': 'http://json-schema.org/draft-04/schema#',
            'description': 'A JSON Schema.',
        })


class AllMessagesJsonSchemaEndpoint(Endpoint, AppAwareFactory):
    NAME = 'schemas'

    def __init__(self, factory, schemas):
        super().__init__(factory, self.NAME, 'GET', '/about/json/schema',
                         NonConfigurableRequestMeta,
                         JsonSchemaResponseMeta)
        self._schemas = schemas

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'schemas'))

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


class ResponseJsonSchemaEndpoint(Endpoint, AppAwareFactory):
    NAME = 'schemas.response'

    @contract
    def __init__(self, factory: Factory, schemas):
        super().__init__(factory, self.NAME, 'GET',
                         '/about/json/schema/response/<endpoint_name>',
                         EndpointRequestMeta,
                         JsonSchemaResponseMeta)
        self._schemas = schemas

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'schemas'))

    def handle(self, request):
        assert isinstance(request, EndpointRequest)
        return JsonSchemaResponse(
            self._schemas.get_for_response(request.endpoint_name))
