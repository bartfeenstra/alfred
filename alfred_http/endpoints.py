import abc
from copy import copy
from typing import Iterable, Optional, Dict

from contracts import contract, ContractsMeta, with_metaclass
from flask import Request as HttpRequest, url_for
from flask import Response as HttpResponse

from alfred import format_iter
from alfred.app import Factory


class Error(Exception):
    @contract
    def __init__(self, code: str, title: str, http_response_status_code: int):
        self._code = code
        self._title = title
        self._http_response_status_code = http_response_status_code

    @property
    @contract
    def code(self) -> str:
        return self._code

    @property
    @contract
    def title(self) -> str:
        return self._title

    @property
    @contract
    def http_response_status_code(self) -> int:
        return self._http_response_status_code


class NotFoundError(Error):
    CODE = 'not_found'

    def __init__(self):
        super().__init__(self.CODE, 'Not found', 404)


class NotAcceptableError(Error):
    CODE = 'not_acceptable'

    def __init__(self):
        super().__init__(self.CODE, 'Not acceptable', 406)


class UnsupportedMediaTypeError(Error):
    CODE = 'unsupported_media_type'

    def __init__(self):
        super().__init__(self.CODE, 'Unsupported media type', 415)


class BadGatewayError(Error):
    CODE = 'bad_gateway'

    def __init__(self):
        super().__init__(self.CODE, 'Bad gateway', 502)


class GatewayTimeoutError(Error):
    CODE = 'gateway_timeout'

    def __init__(self):
        super().__init__(self.CODE, 'Gateway timeout', 504)


class MessageMeta(with_metaclass(ContractsMeta)):
    @contract
    def __init__(self, name: str):
        self._name = name

    @property
    @contract
    def name(self) -> str:
        return self._name

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
    def __init__(self, name: str, method: str):
        super().__init__(name)
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

    @contract
    def __init__(self, method: str):
        super().__init__('non-configurable-%s' % method.lower(), method)

    def from_http_request(self, http_request, parameters):
        return NonConfigurableRequest()

    def get_content_types(self):
        return ['']


class NonConfigurableGetRequestMeta(NonConfigurableRequestMeta):
    def __init__(self):
        super().__init__('GET')


class Response(Message):
    @property
    @abc.abstractmethod
    @contract
    def http_response_status_code(self) -> int:
        pass


class ResponseMeta(MessageMeta):
    @contract
    def to_http_response(self, response: Response, content_type: str) -> HttpResponse:
        """
        Converts an API response to an HTTP response.
        :param response:
        :return:
        """
        assert content_type in self.get_content_types()
        http_response = HttpResponse()
        http_response.status = str(response.http_response_status_code)
        http_response.headers.set('Content-Type', content_type)
        return http_response


class SuccessResponse(Response):
    @property
    def http_response_status_code(self):
        return 200


class SuccessResponseMeta(ResponseMeta):
    pass


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

    @property
    def http_response_status_code(self):
        if 0 == len(self._errors):
            return 500

        # We assume the first error is somehow the most important one.
        return self._errors[0].http_response_status_code


class EmptyResponseMeta(ResponseMeta):
    def __init__(self):
        super().__init__('empty')

    def get_content_types(self):
        return ['']


class ErrorResponseMetaRepository(with_metaclass(ContractsMeta)):
    def __init__(self):
        self._metas = {}

    @contract
    def add_meta(self, meta: ResponseMeta):
        assert meta.name not in self._metas
        self._metas[meta.name] = meta

    @contract
    def get_metas(self) -> Iterable:
        return self._metas.values()


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


class EndpointNotFound(RuntimeError):
    def __init__(self, endpoint_name: str,
                 available_endpoints: Optional[Iterable[Endpoint]] = None):
        available_endpoints = list(
            available_endpoints) if available_endpoints is not None else []
        if not available_endpoints:
            message = 'Could not find endpoint "%s", because there are no endpoints.' % endpoint_name
        else:
            available_names = map(
                lambda endpoint: endpoint.name, available_endpoints)
            message = 'Could not find endpoint "%s". Did you mean one of the following?\n' % endpoint_name + \
                      format_iter(available_names)
        super().__init__(message)


class RequestNotFound(RuntimeError):
    def __init__(self, request_name: str,
                 available_requests: Optional[Iterable[RequestMeta]] = None):
        available_requests = list(
            available_requests) if available_requests is not None else []
        if not available_requests:
            message = 'Could not find requests "%s", because there are no requests, and no endpoints.' % request_name
        else:
            available_names = map(
                lambda request: request.name, available_requests)
            message = 'Could not find request "%s". Did you mean one of the following?\n' % request_name + \
                      format_iter(available_names)
        super().__init__(message)


class ResponseNotFound(RuntimeError):
    def __init__(self, response_name: str,
                 available_responses: Optional[Iterable[ResponseMeta]] = None):
        available_responses = list(
            available_responses) if available_responses is not None else []
        if not available_responses:
            message = 'Could not find response "%s", because there are no responses, and no endpoints.' % response_name
        else:
            available_names = map(
                lambda response: response.name, available_responses)
            message = 'Could not find response "%s". Did you mean one of the following?\n' % response_name + \
                      format_iter(available_names)
        super().__init__(message)


class EndpointRepository(with_metaclass(ContractsMeta)):
    def __init__(self):
        self._request_metas = None
        self._response_metas = None

    def get_endpoint(self, endpoint_name: str) -> Optional[Endpoint]:
        pass

    @contract
    def get_endpoints(self) -> Iterable:
        pass

    def get_request_meta(self, request_name: str) -> Optional[RequestMeta]:
        if self._request_metas is None:
            self._aggregate_metas()

        for request_meta in self._request_metas:
            if request_name == request_meta.name:
                return request_meta
        raise RequestNotFound(request_name, self._request_metas)

    @contract
    def get_request_metas(self) -> Iterable:
        if self._request_metas is None:
            self._aggregate_metas()

        return self._request_metas

    def get_response_meta(self, response_name: str) -> Optional[ResponseMeta]:
        if self._request_metas is None:
            self._aggregate_metas()

        for response_meta in self._response_metas:
            if response_name == response_meta.name:
                return response_meta
        raise ResponseNotFound(response_name, self._response_metas)

    @contract
    def get_response_metas(self) -> Iterable:
        if self._response_metas is None:
            self._aggregate_metas()

        return self._response_metas

    def _aggregate_metas(self):
        request_metas = {}
        response_metas = {}
        for endpoint in self.get_endpoints():
            request_metas.setdefault(
                endpoint.request_meta.name, endpoint.request_meta)
            response_metas.setdefault(
                endpoint.response_meta.name, endpoint.response_meta)
        self._request_metas = request_metas.values()
        self._response_metas = response_metas.values()


class StaticEndpointRepository(EndpointRepository):
    @contract
    def __init__(self, endpoints: Iterable):
        super().__init__()
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
        super().__init__()
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
        super().__init__()
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
        return url_for(endpoint.path, _external=True, **parameters)
