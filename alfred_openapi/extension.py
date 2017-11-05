from alfred.app import Extension
from alfred_http.endpoints import EndpointFactoryRepository, OpenApiEndpoint
from alfred_http.extension import HttpExtension


class OpenApiExtension(Extension):
    @staticmethod
    def name():
        return 'openapi'

    @staticmethod
    def dependencies():
        return [HttpExtension]

    @Extension.service()
    def _openapi(self):
        return OpenApi(self._app.service('http', 'endpoints'),
                       self._app.service('http', 'schemas'))

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            OpenApiEndpoint,
        ])
