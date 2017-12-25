from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_rest import json_schema
from alfred_rest.endpoints import JsonSchemaEndpoint, \
    ExternalJsonSchemaEndpoint, RestErrorResponseMeta
from alfred_rest.json import Validator, NestedRewriter, \
    IdentifiableDataTypeAggregator, \
    ExternalReferenceProxy, SchemaRepository


class RestExtension(Extension):
    @staticmethod
    def name():
        return 'rest'

    @staticmethod
    def dependencies():
        return [HttpExtension, CoreExtension]

    @Extension.service()
    def _json_validator(self) -> Validator:
        return Validator(self._app.service('rest', 'json_schema_rewriter'))

    @Extension.service()
    def _json_schema_rewriter(self):
        rewriter = NestedRewriter()
        for tagged_rewriter in self._app.services(tag='json_schema_rewriter'):
            rewriter.add_rewriter(tagged_rewriter)
        return rewriter

    @Extension.service(tags=('json_schema_rewriter',))
    def _internal_reference_aggregator(self):
        return IdentifiableDataTypeAggregator(
            self._app.service('http', 'urls'))

    @Extension.service(tags=('json_schema_rewriter',))
    def _external_reference_proxy(self):
        return ExternalReferenceProxy(self._app.service('http', 'base_url'),
                                      self._app.service('http', 'urls'))

    @Extension.service()
    def _json_schemas(self):
        schemas = SchemaRepository()
        for tagged_schema in self._app.services(tag='json_schema'):
            schemas.add_schema(tagged_schema)
        return schemas

    @Extension.service(tags=('json_schema',))
    def _json_schema(self):
        return json_schema()

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            JsonSchemaEndpoint,
            ExternalJsonSchemaEndpoint,
        ])

    @Extension.service(tags=('error_response_meta',))
    def _rest_error_response_meta(self):
        return RestErrorResponseMeta(self._app.service('http', 'urls'))
