import json

from apispec import APISpec
from contracts import contract
from jinja2 import Template

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import SuccessResponse, SuccessResponseMeta, \
    Endpoint, NonConfigurableRequest, \
    NonConfigurableGetRequestMeta
from alfred_openapi import RESOURCE_PATH


class OpenApiResponse(SuccessResponse):
    @contract
    def __init__(self, spec: APISpec):
        super().__init__()
        self._spec = spec

    @property
    def spec(self) -> APISpec:
        return self._spec


class OpenApiResponseMeta(SuccessResponseMeta):
    def to_http_response(self, response, content_type):
        assert isinstance(response, OpenApiResponse)
        http_response = super().to_http_response(response, content_type)
        if 'application/json' == content_type:
            return self._to_json(http_response, response)
        if 'text/html' == content_type:
            return self._to_html(http_response, response)

    def _to_html(self, http_response, response):
        template = Template(
            open(RESOURCE_PATH + '/templates/redoc.html.j2').read())
        # @todo Use the URL builder to get the URL to this endpoint.
        spec_url = 'http://127.0.0.1:5000/about/openapi'
        http_response.set_data(template.render(spec_url=spec_url))
        return http_response

    def _to_json(self, http_response, response):
        http_response.set_data(json.dumps(response.spec.to_dict()))
        return http_response

    def get_content_types(self):
        return ['application/json', 'text/html']


class OpenApiEndpoint(Endpoint, AppAwareFactory):
    NAME = 'openapi'

    @contract
    def __init__(self, factory: Factory, openapi):
        super().__init__(factory, self.NAME, '/about/openapi',
                         NonConfigurableGetRequestMeta, OpenApiResponseMeta)
        self._openapi = openapi

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('openapi', 'openapi'))

    def handle(self, request):
        assert isinstance(request, NonConfigurableRequest)
        return OpenApiResponse(self._openapi.get())
