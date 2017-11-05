from alfred.app import Extension
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_openapi.endpoints import OpenApiEndpoint
from alfred_openapi.openapi import OpenApi


class OpenApiExtension(Extension):
    @staticmethod
    def name():
        return 'openapi'

    @staticmethod
    def dependencies():
        return [HttpExtension]

    @Extension.service()
    def _openapi(self):
        return OpenApi(self._app.service('http', 'endpoints'))

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            OpenApiEndpoint,
        ])
