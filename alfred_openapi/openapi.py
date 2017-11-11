from apispec import APISpec
from contracts import contract

from alfred_http.endpoints import EndpointRepository


class OpenApi:
    @contract
    def __init__(self, endpoints: EndpointRepository):
        self._endpoints = endpoints

    @contract
    def get(self) -> APISpec:
        # @todo How to determine the API version?
        spec = APISpec('Alfred', '0.0.0')

        paths_operations = {}
        for endpoint in self._endpoints.get_endpoints():
            method = endpoint.request_meta.method.lower()

            operations = {
                'operationId': endpoint.name,
                'consumes': endpoint.request_meta.get_content_types(),
                'produces': endpoint.response_meta.get_content_types(),
                'responses': {
                    200: {
                        'description': 'A successful response.',
                    },
                },
            }

            paths_operations.setdefault(endpoint.path, {})
            paths_operations[endpoint.path].setdefault(method, {})
            paths_operations[endpoint.path][method] = operations

        for path, operations in paths_operations.items():
            spec.add_path(path, operations)
        return spec
