import json

from apispec import APISpec
from contracts import contract

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import SuccessResponse, SuccessResponseMeta, \
    Endpoint, NonConfigurableRequest, \
    NonConfigurableGetRequestMeta


class OpenApiResponse(SuccessResponse):
    @contract
    def __init__(self, spec: APISpec):
        super().__init__()
        self._spec = spec

    @property
    def spec(self) -> APISpec:
        return self._spec


class OpenApiResponseMeta(SuccessResponseMeta):
    def to_http_response(self, response):
        assert isinstance(response, OpenApiResponse)
        http_response = super().to_http_response(response)
        http_response.set_data(json.dumps(response.spec.to_dict()))
        return http_response

    def get_content_type(self):
        return 'application/json'


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
