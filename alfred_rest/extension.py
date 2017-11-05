from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import EndpointFactoryRepository, \
    ResponseJsonSchemaEndpoint, AllMessagesJsonSchemaEndpoint
from alfred_http.extension import HttpExtension
from alfred_openapi.extension import OpenApiExtension


class RestExtension(Extension):
    @staticmethod
    def name():
        return 'rest'

    @staticmethod
    def dependencies():
        return [OpenApiExtension, HttpExtension, CoreExtension]

    @Extension.service()
    def _schemas(self):
        return SchemaRepository(self._app.service('http', 'endpoints'),
                                self._app.service('http', 'urls'))

    @Extension.service()
    def _json_validator(self) -> Validator:
        return Validator()

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            AllMessagesJsonSchemaEndpoint,
            ResponseJsonSchemaEndpoint,
        ])
