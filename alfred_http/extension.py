from typing import Iterable

from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import EndpointUrlBuilder, \
    AllMessagesJsonSchemaEndpoint, \
    ResponseJsonSchemaEndpoint, NestedEndpointRepository, \
    EndpointFactoryRepository
from alfred_http.json import Validator
from alfred_http.schemas import SchemaRepository


class HttpExtension(Extension):
    @staticmethod
    def name():
        return 'http'

    @staticmethod
    def dependencies():
        return [CoreExtension]

    @Extension.service()
    def _endpoints(self):
        endpoints = NestedEndpointRepository()
        for tagged_endpoints in self._app.services(tag='http_endpoints'):
            endpoints.add_endpoints(tagged_endpoints)
        return endpoints

    @Extension.service(tags=('http_endpoints',))
    def _endpoints_http(self):
        return EndpointFactoryRepository(self._app.factory, [
            AllMessagesJsonSchemaEndpoint,
            ResponseJsonSchemaEndpoint,
        ])

    @Extension.service()
    def _schemas(self):
        return SchemaRepository(self._app.service('http', 'endpoints'),
                                self._app.service('http', 'urls'))

    @Extension.service()
    def _urls(self):
        return EndpointUrlBuilder(self._app.service('http', 'endpoints'))

    @Extension.service()
    def _json_validator(self) -> Validator:
        return Validator()
