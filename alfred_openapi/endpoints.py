from apispec import APISpec
from contracts import contract

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import SuccessResponse, SuccessResponseMeta, \
    Endpoint, NonConfigurableRequestMeta, NonConfigurableRequest
from alfred_rest.json import Json


class OpenApiResponse(SuccessResponse):
    @contract
    def __init__(self, spec: APISpec):
        super().__init__()
        self._has_data = True
        self._data = spec.to_dict()


class OpenApiResponseMeta(SuccessResponseMeta):
    def to_http_response(self, response):
        assert isinstance(response, OpenApiResponse)
        return super().to_http_response(response)

    def get_payload_schema(self):
        # @todo Move this to a new alfred_json_api (or w/e) module, so alfred_http
        #  can be used for all kinds of HTTP endpoints.
        # @todo Instead, use parameter and payload validation here, and in the JSON
        # subclasses use the endpoints' schemas for the implementations.
        return Json.from_data({
            # @todo Consider serving this from our own endpoint, so we can
            # ensure the correct content type is set, and clients don't run
            # into errors.
            '$ref': 'https://raw.githubusercontent.com/OAI/OpenAPI-Specification/master/schemas/v2.0/schema.json#',
            'description': 'The API specification in the OpenAPI (Swagger) 2.0 format.',
        })


class OpenApiEndpoint(Endpoint, AppAwareFactory):
    NAME = 'openapi'

    @contract
    def __init__(self, factory: Factory, openapi):
        super().__init__(factory, self.NAME, 'GET', '/about/openapi',
                         NonConfigurableRequestMeta, OpenApiResponseMeta)
        self._openapi = openapi

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'openapi'))

    def handle(self, request):
        assert isinstance(request, NonConfigurableRequest)
        return OpenApiResponse(self._openapi.get())
