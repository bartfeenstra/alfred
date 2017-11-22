from alfred.app import Extension
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_openapi.endpoints import OpenApiEndpoint
from alfred_openapi.openapi import OpenApi
from alfred_rest.endpoints import build_external_schema_endpoint
from alfred_rest.extension import RestExtension


class OpenApiExtension(Extension):
    @staticmethod
    def name():
        return 'openapi'

    @staticmethod
    def dependencies():
        return [RestExtension, HttpExtension]

    @Extension.service()
    def _openapi(self):
        return OpenApi(self._app.service('http', 'endpoints'))

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            OpenApiEndpoint,
            build_external_schema_endpoint('openapi', 'https://raw.githubusercontent.com/OAI/OpenAPI-Specification/master/schemas/v2.0/schema.json'),
        ])
