from typing import Iterable

from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import EndpointUrlBuilder, \
    AllMessagesJsonSchemaEndpoint, \
    ResponseJsonSchemaEndpoint, StaticEndpointRepository, \
    NestedEndpointRepository
from alfred_http.json import Validator
from alfred_http.schemas import SchemaRepository


class HttpExtension(Extension):
    @staticmethod
    def name():
        return 'http'

    @staticmethod
    def dependencies() -> Iterable:
        return [CoreExtension]

    @Extension.service()
    def _endpoints(self):
        endpoints = NestedEndpointRepository()
        for tagged_endpoints in self._app.services(tag='http_endpoints'):
            endpoints.add_endpoints(tagged_endpoints)
        return endpoints

    @Extension.service(tags=('http_endpoints',))
    def _endpoints_http(self):
        endpoints = [
            AllMessagesJsonSchemaEndpoint(
                self._app.service('http', 'schemas')),
            ResponseJsonSchemaEndpoint(self._app.service('http', 'schemas')),
        ]
        return StaticEndpointRepository(endpoints)

    @Extension.service()
    def _schemas(self) -> SchemaRepository:
        return SchemaRepository(self._app.service('http', 'endpoints'),
                                self._app.service('core', 'urls'))

    @Extension.service()
    def _urls(self) -> EndpointUrlBuilder:
        return EndpointUrlBuilder(self._app.service('http', 'endpoints'))

    @Extension.service()
    def _json_validator(self) -> Validator:
        return Validator()
