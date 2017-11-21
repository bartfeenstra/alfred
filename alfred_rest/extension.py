from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_openapi.extension import OpenApiExtension
from alfred_rest.endpoints import JsonSchemaEndpoint
from alfred_rest.json import Validator


class RestExtension(Extension):
    @staticmethod
    def name():
        return 'rest'

    @staticmethod
    def dependencies():
        return [OpenApiExtension, HttpExtension, CoreExtension]

    @Extension.service()
    def _json_validator(self) -> Validator:
        return Validator()

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            JsonSchemaEndpoint,
        ])
