from alfred.app import Extension
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_openapi import openapi_schema
from alfred_openapi.endpoints import OpenApiEndpoint
from alfred_openapi.openapi import OpenApi
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
        return OpenApi(self._app.service('http', 'endpoints'), self._app.service('http', 'urls'))

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            OpenApiEndpoint,
        ])

    @Extension.service(tags=('json_schema',))
    def _openapi_schema(self):
        return openapi_schema()
