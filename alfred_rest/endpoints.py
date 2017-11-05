from contracts import contract

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import SuccessResponse, SuccessResponseMeta, \
    Endpoint, NonConfigurableRequestMeta, Request, RequestMeta
from alfred_rest.json import Json


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
