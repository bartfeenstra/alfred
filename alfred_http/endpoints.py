import abc
from copy import copy
from typing import Iterable, Optional, Dict

from contracts import contract, ContractsMeta, with_metaclass
from flask import Request as HttpRequest, url_for
from flask import Response as HttpResponse

from alfred import format_iter
from alfred.app import Factory
from alfred.extension import AppAwareFactory


# @todo RESOURCE/ENDPOINT
# @todo - Has a path (must map to request type requirements)
# @todo - Has request and response types.
# @todo - Can map Content-Type headers to the available request payload formats.
# @todo - Can map Accept headers to the available response payload formats.
# @todo
# @todo MESSAGE TYPE/META
# @todo - Has requirements that can be mapped to a payload.
# @todo - Not specific to endpoints.
# @todo - Payload conversion can be pluggable, and available payload formats can be exposed.
# @todo - Can have no payload, and no payload format.
# @todo - It must be easy to support but one format and message factory.
# @todo
# @todo REQUEST TYPE/META
# @todo - Has requirements that can be mapped to a path.
# @todo - Has an HTTP method.
# @todo
# @todo RESPONSE TYPE/META
# @todo
# @todo ===BELOW CAN BE DONE LATER===
# @todo
# @todo MESSAGE FACTORIES
# @todo - Take request requirements and return Commands
# @todo - Take Results and return response requirements
# @todo
# @todo DATA FACTORIES
# @todo - Serialize and serialize internal types to and from payload formats
# @todo
# @todo
# @todo
# @todo
# @todo
# @todo
# @todo
# @todo


class Error(Exception):
    @contract
    def __init__(self, code: str):
        self._code = code

    @property
    def code(self):
        return self._code


class MessageMeta(AppAwareFactory,
                  with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    def get_content_types(self) -> Iterable[str]:
        pass


class Message(with_metaclass(ContractsMeta)):
    pass


class Request(Message):
    pass


class RequestMeta(MessageMeta):
    _allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

    @contract
    def __init__(self, method: str):
        method = method.upper()
        assert method in self._allowed_methods
        self._method = method

    @abc.abstractmethod
    @contract
    def from_http_request(self, http_request: HttpRequest,
                          parameters: Dict) -> Request:
        """
        Converts an HTTP request to an API request.

        The HTTP request SHOULD be valid for this request. If it is not,
        exceptions may be raised.
        :param http_request:
        :param parameters:
        :return:
        """
        pass

    @property
    def method(self) -> str:
        return self._method


class NonConfigurableRequest(Request):
    pass


class NonConfigurableRequestMeta(RequestMeta):
    """
    Defines a non-configurable request.
    """

    def from_http_request(self, http_request, parameters):
        return NonConfigurableRequest()

    def get_content_types(self):
        return []


class NonConfigurableGetRequestMeta(NonConfigurableRequestMeta):
    def __init__(self):
        super().__init__('GET')


class Response(Message):
    pass


class ResponseMeta(MessageMeta):
    @contract
    def to_http_response(self, response, content_type: str) -> HttpResponse:
        """
        Converts an API response to an HTTP response.
        :param response:
        :return:
        """
        assert content_type in self.get_content_types()
        http_response = HttpResponse()
        http_response.headers.set('Content-Type', content_type)
        return http_response


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
    def to_http_response(self, response, content_type):
        http_response = super().to_http_response(response, content_type)
        http_response.status = '200'
        return http_response


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
    @contract
    def __init__(self, factory: Factory, name: str, path: str,
                 request_meta_class: type,
                 response_meta_class: type):
        assert issubclass(request_meta_class, RequestMeta)
        assert issubclass(response_meta_class, ResponseMeta)
        self._name = name
        self._path = path
        self._request_meta = factory.defer(request_meta_class)
        self._response_meta = factory.defer(response_meta_class)

    @property
    def name(self) -> str:
        return self._name

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

    @abc.abstractmethod
    @contract
    def handle(self, request: Request) -> Response:
        pass
        # @todo There is a certain type of problem we cannot find just in RequestMeta or ResponseMeta.
        # @todo This type (usually) doesn't just touch one type of message, but both.
        # @todo An example is Accept-Type, a request header dependent on response capabilities.
        # @todo Where do we check this? RequestMeta does not know about ResponseMeta and vice versa.
        # @todo Endpoints do not know about HTTP messages (and I would like to keep it that way).
        # @todo Should we do this in our Flask view after all?
        pass


class EndpointNotFound(RuntimeError):
    def __init__(self, endpoint_name: str,
                 available_endpoints: Optional[Iterable[Endpoint]] = None):
        available_endpoints = list(
            available_endpoints) if available_endpoints is not None else []
        if not available_endpoints:
            message = 'Could not find endpoint "%s", because there are no endpoints.' % endpoint_name
        else:
            available_endpoint_names = map(
                lambda endpoint: endpoint.name, available_endpoints)
            message = 'Could not find endpoint "%s". Did you mean one of the following?\n' % endpoint_name + \
                      format_iter(available_endpoint_names)
        super().__init__(message)


class EndpointRepository(with_metaclass(ContractsMeta)):
    def get_endpoint(self, endpoint_name: str) -> Optional[Endpoint]:
        pass

    @contract
    def get_endpoints(self) -> Iterable:
        pass


class StaticEndpointRepository(EndpointRepository):
    @contract
    def __init__(self, endpoints: Iterable):
        self._endpoints = endpoints

    def get_endpoint(self, endpoint_name: str):
        for endpoint in self._endpoints:
            if endpoint_name == endpoint.name:
                return endpoint
        raise EndpointNotFound(endpoint_name, self._endpoints)

    def get_endpoints(self):
        return self._endpoints


class EndpointFactoryRepository(EndpointRepository):
    @contract
    def __init__(self, factory: Factory, endpoint_classes: Iterable):
        self._factory = factory
        self._endpoint_classes = endpoint_classes
        self._endpoints = None

    def get_endpoint(self, endpoint_name: str):
        if self._endpoints is None:
            self._aggregate_endpoints()

        for endpoint in self._endpoints:
            if endpoint_name == endpoint.name:
                return endpoint
        raise EndpointNotFound(endpoint_name, self._endpoints)

    def get_endpoints(self):
        if self._endpoints is None:
            self._aggregate_endpoints()
        return self._endpoints

    def _aggregate_endpoints(self):
        self._endpoints = []
        for endpoint_class in self._endpoint_classes:
            endpoint = self._factory.new(endpoint_class)
            assert isinstance(endpoint, Endpoint)
            self._endpoints.append(endpoint)


class NestedEndpointRepository(EndpointRepository):
    def __init__(self):
        self._endpoints = None
        self._endpoint_repositories = []

    @contract
    def add_endpoints(self, repositories: EndpointRepository):
        # Re-set the aggregated endpoints.
        self._endpoints = None
        self._endpoint_repositories.append(repositories)

    def get_endpoint(self, endpoint_name: str):
        if self._endpoints is None:
            self._aggregate_endpoints()

        for endpoint in self._endpoints:
            if endpoint_name == endpoint.name:
                return endpoint
        raise EndpointNotFound(endpoint_name, self._endpoints)

    def get_endpoints(self):
        if self._endpoints is None:
            self._aggregate_endpoints()
        return self._endpoints

    def _aggregate_endpoints(self):
        self._endpoints = []
        for repository in self._endpoint_repositories:
            for endpoint in repository.get_endpoints():
                self._endpoints.append(endpoint)


class EndpointUrlBuilder:
    @contract
    def __init__(self, endpoints: EndpointRepository):
        self._endpoints = endpoints

    def build(self, endpoint_name: str, parameters: Optional[Dict] = None):
        endpoint = self._endpoints.get_endpoint(endpoint_name)
        if parameters is None:
            parameters = {}
        return url_for(endpoint.path, **parameters)
