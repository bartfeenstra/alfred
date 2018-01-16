from apispec import APISpec
from contracts import contract
from jinja2 import Template

from alfred.app import App
from alfred_http.endpoints import Endpoint, NonConfigurableGetRequestType, \
    SuccessResponse, ResponseType, ResponsePayloadType
from alfred_http.http import HttpBody, HttpResponseBuilder
from alfred_json.type import OutputDataType
from alfred_openapi import RESOURCE_PATH
from alfred_rest.endpoints import JsonResponsePayloadType


class OpenApiResponse(SuccessResponse):
    @contract
    def __init__(self, spec: APISpec):
        super().__init__()
        self._spec = spec

    @property
    def spec(self) -> APISpec:
        return self._spec


class OpenApiSpecificationType(OutputDataType):
    def to_json(self, data):
        assert isinstance(data, OpenApiResponse)
        return data.spec.to_dict()

    def get_json_schema(self):
        return {
            '$ref': 'http://swagger.io/v2/schema.json#',
        }


class ReDocResponsePayloadType(ResponsePayloadType):
    def __init__(self):
        self._urls = App.current.service('http', 'urls')

    def get_content_types(self):
        return ['text/html']

    def to_http_response(self, response, content_type):
        http_response = HttpResponseBuilder()
        template = Template(
            open(RESOURCE_PATH + '/templates/redoc.html.j2').read())
        spec_url = self._urls.build('openapi')
        http_response.body = HttpBody(template.render(spec_url=spec_url),
                                      content_type)
        return http_response


class OpenApiResponseType(ResponseType):
    def __init__(self):
        super().__init__('openapi',
                         (JsonResponsePayloadType(OpenApiSpecificationType()),
                          ReDocResponsePayloadType()))
        self._urls = App.current.service('http', 'urls')


class OpenApiEndpoint(Endpoint):
    def __init__(self):
        super().__init__('openapi', '/about/openapi',
                         NonConfigurableGetRequestType(),
                         OpenApiResponseType())
        self._openapi = App.current.service('openapi', 'openapi')

    def handle(self, request):
        return OpenApiResponse(self._openapi.get())
