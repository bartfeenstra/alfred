from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_rest.endpoints import JsonSchemaEndpoint, \
    ExternalJsonSchemaEndpoint
from alfred_rest.json import Validator, Rewriter


class RestExtension(Extension):
    @staticmethod
    def name():
        return 'rest'

    @staticmethod
    def dependencies():
        return [HttpExtension, CoreExtension]

    @Extension.service()
    def _json_validator(self) -> Validator:
        return Validator()

    @Extension.service()
    def _json_reference_rewriter(self) -> Rewriter:
        return Rewriter(self._app.service('http', 'base_url'), self._app.service('http', 'urls'))

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            JsonSchemaEndpoint,
            ExternalJsonSchemaEndpoint,
        ])
