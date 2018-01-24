from alfred.app import Extension, App
from alfred_http.endpoints import EndpointFactoryRepository
from alfred_http.extension import HttpExtension
from alfred_rest.endpoints import JsonSchemaEndpoint, \
    ExternalJsonSchemaEndpoint, ResourceEndpointRepository, ErrorPayloadType
from alfred_rest.json import ExternalReferenceProxy
from alfred_rest.schema import AlfredJsonSchema


class RestExtension(Extension):
    @staticmethod
    def name():
        return 'rest'

    @staticmethod
    def dependencies():
        return [HttpExtension]

    @Extension.service(tags=('json_schema_rewriter',))
    def _external_reference_proxy(self):
        return ExternalReferenceProxy(App.current.service('http', 'base_url'),
                                      App.current.service('http', 'urls'))

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

    @Extension.service(tags=('error_response_payload_type',))
    def _rest_error_response_payload_type(self):
        return ErrorPayloadType()

    @Extension.service()
    def _resources(self):
        resources = {}
        for tagged_resources in App.current.services(tag='resources'):
            resources[tagged_resources.get_type().name] = tagged_resources
        return resources

    @Extension.service(tags=('json_schema',))
    def _alfred_json_schema(self):
        return AlfredJsonSchema().get()
