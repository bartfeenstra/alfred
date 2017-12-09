from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_rest.endpoints import JsonSchemaEndpoint, \
    ExternalJsonSchemaReferenceProxyEndpoint
from alfred_rest.json import Validator, NestedRewriter, \
    IdentifiableDataTypeAggregator, \
    ExternalReferenceProxy


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
    def _json_schema_rewriter(self):
        rewriter = NestedRewriter()
        for tagged_rewriter in self._app.services(tag='json_schema_rewriter'):
            rewriter.add_rewriter(tagged_rewriter)
        return rewriter

    @Extension.service(tags=('json_schema_rewriter',))
    def _internal_reference_aggregator(self):
        return IdentifiableDataTypeAggregator()

    @Extension.service(tags=('json_schema_rewriter',))
    def _external_reference_proxy(self):
        return ExternalReferenceProxy(self._app.service('http', 'base_url'),
                                      self._app.service('http', 'urls'))

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            JsonSchemaEndpoint,
            ExternalJsonSchemaReferenceProxyEndpoint,
        ])
