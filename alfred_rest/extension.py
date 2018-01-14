from alfred.app import Extension, App
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_rest import json_schema
from alfred_rest.endpoints import JsonSchemaEndpoint, \
    ExternalJsonSchemaEndpoint, RestErrorResponseType, \
    ResourceEndpointRepository
from alfred_rest.json import Validator, NestedRewriter, \
    IdentifiableDataTypeAggregator, \
    ExternalReferenceProxy, SchemaRepository


class RestExtension(Extension):
    @staticmethod
    def name():
        return 'rest'

    @staticmethod
    def dependencies():
        return [HttpExtension]

    @Extension.service()
    def _json_validator(self) -> Validator:
        return Validator(App.current.service('rest', 'external_reference_proxy'))

    @Extension.service()
    def _json_schema_rewriter(self):
        rewriter = NestedRewriter()
        for tagged_rewriter in App.current.services(
                tag='json_schema_rewriter'):
            rewriter.add_rewriter(tagged_rewriter)
        return rewriter

    @Extension.service(tags=('json_schema_rewriter',))
    def _identifiable_data_type_aggregator(self):
        return IdentifiableDataTypeAggregator()

    @Extension.service(tags=('json_schema_rewriter',))
    def _external_reference_proxy(self):
        return ExternalReferenceProxy(App.current.service('http', 'base_url'),
                                      App.current.service('http', 'urls'))

    @Extension.service()
    def _json_schemas(self):
        schemas = SchemaRepository()
        for tagged_schema in App.current.services(tag='json_schema'):
            schemas.add_schema(tagged_schema)
        return schemas

    @Extension.service(tags=('json_schema',))
    def _json_schema(self):
        return json_schema()

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository([
            JsonSchemaEndpoint,
            ExternalJsonSchemaEndpoint,
        ])

    @Extension.service(tags=('http_endpoints',))
    def _resource_endpoints(self):
        return ResourceEndpointRepository(
            App.current.service('rest', 'resources').values())

    @Extension.service(tags=('error_response_type',))
    def _rest_error_response_type(self):
        return RestErrorResponseType()

    @Extension.service()
    def _resources(self):
        resources = {}
        for tagged_resources in App.current.services(tag='resources'):
            resources[tagged_resources.get_type().name] = tagged_resources
        return resources
