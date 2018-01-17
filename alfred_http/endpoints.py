import abc
from copy import copy
from typing import Iterable, Optional, Dict

from contracts import contract, ContractsMeta, with_metaclass
from flask import url_for

from alfred import format_iter
from alfred.app import App
from alfred.functools import dispatch
from alfred_http.http import HttpRequest, HttpResponse, HttpResponseBuilder
from alfred_json.type import IdentifiableScalarType, InputDataType


class Error(Exception):
    @contract
    def __init__(self, code: str, title: str, http_response_status_code: int,
                 description=''):
        self._code = code
        self._title = title
        self._description = description
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
    def description(self) -> str:
        return self._description

    @property
    @contract
    def http_response_status_code(self) -> int:
        return self._http_response_status_code


class NotFoundError(Error):
    CODE = 'not_found'

    def __init__(self, **kwargs):
        super().__init__(self.CODE, 'Not found', 404, **kwargs)


class NotAcceptableError(Error):
    CODE = 'not_acceptable'

    def __init__(self, **kwargs):
        super().__init__(self.CODE, 'Not acceptable', 406, **kwargs)


class UnsupportedMediaTypeError(Error):
    CODE = 'unsupported_media_type'

    def __init__(self, **kwargs):
        super().__init__(self.CODE, 'Unsupported media type', 415, **kwargs)


class BadGatewayError(Error):
    CODE = 'bad_gateway'

    def __init__(self, **kwargs):
        super().__init__(self.CODE, 'Bad gateway', 502, **kwargs)


class GatewayTimeoutError(Error):
    CODE = 'gateway_timeout'

    def __init__(self, **kwargs):
        super().__init__(self.CODE, 'Gateway timeout', 504, **kwargs)


class MessageType(with_metaclass(ContractsMeta)):
    @contract
    def __init__(self, name: str):
        self._name = name

    @property
    @contract
    def name(self) -> str:
        return self._name


class Message(with_metaclass(ContractsMeta)):
    pass


class PayloadType(with_metaclass(ContractsMeta)):
    @abc.abstractmethod
    def get_content_types(self) -> Iterable[str]:
        pass


class Request(Message):
    pass


class RequestParameter:
    @contract
    def __init__(self, data_type: IdentifiableScalarType, name=None,
                 required=True,
                 cardinality=1):
        assert isinstance(data_type, InputDataType)
        self.assert_valid_type(data_type.get_json_schema())
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


class RequestPayloadType(PayloadType):
    @abc.abstractmethod
    @contract
    def from_http_request(self, http_request: HttpRequest) -> Request:
        """
        Converts an HTTP request to an API request.

        The HTTP request MUST be valid for this request. If it is not,
        developer-facing exceptions may be raised.
        :param http_request:
        :return:
        """
        pass


class RequestType(MessageType):
    _allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

    @contract
    def __init__(self, name: str, method: str, payload_types: Iterable):
        super().__init__(name)
        method = method.upper()
        assert method in self._allowed_methods
        self._method = method
        self._payload_types = payload_types

    @contract
    def from_http_request(self, http_request: HttpRequest) -> Request:
        """
        Converts an HTTP request to an API request.

        The HTTP request SHOULD be valid for this request. If it is not,
        exceptions may be raised.
        :param http_request:
        :return:
        """
        content_type = http_request.body.content_type if http_request.body else ''
        for payload_type in self._payload_types:
            if content_type in payload_type.get_content_types():
                return payload_type.from_http_request(http_request)

        raise UnsupportedMediaTypeError(description='Could not parse the "%s" HTTP payload for request "%s"' % (
            content_type, self.name))

    @property
    def method(self) -> str:
        return self._method

    @dispatch()
    def validate_http_request(self, http_request: HttpRequest):
        """
        Validates an incoming HTTP request.
        :param http_request:
        :return:
        """
        pass

    @validate_http_request.register()
    @contract
    def _validate_http_request_arguments(self, http_request: HttpRequest):
        validator = App.current.service('json', 'validator')
        for parameter in self.get_parameters():
            name = parameter.name
            if parameter.required and name not in http_request.arguments:
                raise RuntimeError(
                    'Request type "%s" (%s) requires URL path parameter "%s". Make sure the endpoint defines this parameter in its path.' % (
                        self.name, type(self), name))
            validator.validate(
                http_request.arguments[name], parameter.type)

    @contract
    def get_payload_types(self) -> Iterable:
        """
        :return: Iterable[RequestPayloadType]
        """
        return self._payload_types

    @contract
    def get_parameters(self) -> Iterable:
        """
        :return: Iterable[RequestParameter]
        """
        return ()


class NonConfigurableRequest(Request):
    pass


class NonConfigurableRequestType(RequestType):
    """
    Defines a non-configurable request.
    """

    @contract
    def __init__(self, method: str):
        super().__init__('non-configurable-%s' % method.lower(), method,
                         (EmptyPayloadType(),))

    def from_http_request(self, http_request):
        return NonConfigurableRequest()


class NonConfigurableGetRequestType(NonConfigurableRequestType):
    def __init__(self):
        super().__init__('GET')


class Response(Message):
    @property
    @abc.abstractmethod
    @contract
    def http_response_status_code(self) -> int:
        pass


class ResponsePayloadType(PayloadType):
    @abc.abstractmethod
    @contract
    def to_http_response(self, response: Response,
                         content_type: str) -> HttpResponseBuilder:
        """
        Converts an API response to an HTTP response.
        :param response: Response
        :return: HttpBody
        """
        pass


class ResponseType(MessageType):
    @contract
    def __init__(self, name, payload_types: Iterable):
        super().__init__(name)
        self._payload_types = payload_types

    @contract
    def get_payload_types(self) -> Iterable:
        """
        :return: Iterable[ResponsePayloadType]
        """
        return self._payload_types

    @contract
    def to_http_response(self, response: Response,
                         content_type: str) -> HttpResponse:
        """
        Converts an API response to an HTTP response.
        :param response:
        :return:
        """
        http_response = None
        for payload_type in self._payload_types:
            if content_type in payload_type.get_content_types():
                http_response = payload_type.to_http_response(
                    response, content_type)
                break
        if not http_response:
            raise RuntimeError(
                'Could not build a "%s" HTTP body for response "%s"' % (
                    content_type, self.name))
        http_response.status = response.http_response_status_code
        return http_response.to_response()


class SuccessResponse(Response):
    @property
    def http_response_status_code(self):
        return 200


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


class ErrorResponseType(ResponseType):
    def __init__(self):
        super().__init__('error', App.current.services(
            tag='error_response_payload_type'))


class EmptyPayloadType(RequestPayloadType, ResponsePayloadType):
    def get_content_types(self):
        return '',

    def from_http_request(self, http_request: HttpRequest):
        return NonConfigurableRequest()

    def to_http_response(self, response, content_type):
        return HttpResponseBuilder()


class EmptyResponseType(ResponseType):
    def __init__(self):
        super().__init__('empty', (EmptyPayloadType(),))


class Endpoint(with_metaclass(ContractsMeta)):
    @contract
    def __init__(self, name: str, path: str,
                 request_type: RequestType,
                 response_type: ResponseType):
        self._name = name
        self._path = path
        self._request_type = request_type
        self._response_type = response_type

    @property
    @contract
    def name(self) -> str:
        return self._name

    @property
    @contract
    def path(self) -> str:
        return self._path

    @property
    @contract
    def request_type(self) -> RequestType:
        return self._request_type

    @property
    @contract
    def response_type(self) -> ResponseType:
        return self._response_type

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
                 available_requests: Optional[Iterable[RequestType]] = None):
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
                 available_responses: Optional[Iterable[ResponseType]] = None):
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
    def get_endpoint(self, endpoint_name: str) -> Optional[Endpoint]:
        endpoints = self.get_endpoints()
        for endpoint in endpoints:
            if endpoint_name == endpoint.name:
                return endpoint
        raise EndpointNotFound(endpoint_name, endpoints)

    @contract
    def get_endpoints(self) -> Iterable:
        pass


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
    def __init__(self, endpoint_classes: Iterable):
        super().__init__()
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
            self._endpoints.append(endpoint_class())


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
