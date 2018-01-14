import json

from apispec import APISpec
from contracts import contract
from jinja2 import Template

from alfred.app import App
from alfred_http.endpoints import Endpoint, NonConfigurableRequest, \
    NonConfigurableGetRequestType, SuccessResponse, \
    ResponseType
from alfred_http.http import HttpBody
from alfred_openapi import RESOURCE_PATH
from alfred_rest.endpoints import JsonMessageType


class OpenApiResponse(SuccessResponse):
    @contract
    def __init__(self, spec: APISpec):
        super().__init__()
        self._spec = spec

    @property
    def spec(self) -> APISpec:
        return self._spec


class OpenApiResponseType(ResponseType, JsonMessageType):
    def __init__(self):
        super().__init__('openapi')
        self._urls = App.current.service('http', 'urls')

    @ResponseType._build_http_response.register()
    def _build_http_response_body(self, response, content_type, http_response):
        assert isinstance(response, OpenApiResponse)
        if 'application/json' == content_type:
            builder = self._to_json
        if 'text/html' == content_type:
            builder = self._to_html
        http_response.body = HttpBody(builder(http_response, response),
                                      content_type)

    def _to_html(self, http_response, response):
        template = Template(
            open(RESOURCE_PATH + '/templates/redoc.html.j2').read())
        spec_url = self._urls.build('openapi')
        return template.render(spec_url=spec_url)

    def _to_json(self, http_response, response):
        return json.dumps(response.spec.to_dict())

    def get_content_types(self):
        return super().get_content_types() + ['text/html']

    def get_json_schema(self):
        return {
            '$ref': 'http://swagger.io/v2/schema.json#',
            'description': 'An OpenAPI/Swagger 2.0 schema.',
        }


class OpenApiEndpoint(Endpoint):
    NAME = 'openapi'

    def __init__(self):
        super().__init__(self.NAME, '/about/openapi',
                         NonConfigurableGetRequestType(),
                         OpenApiResponseType())
        self._openapi = App.current.service('openapi', 'openapi')

    def handle(self, request):
        assert isinstance(request, NonConfigurableRequest)
        return OpenApiResponse(self._openapi.get())
