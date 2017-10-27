from typing import Optional

from contracts import contract

from alfred import RESOURCE_PATH
from alfred_http.endpoints import EndpointRepository, EndpointUrlBuilder
from alfred_http.json import Json


class SchemaRepository:
    def __init__(self, endpoints: EndpointRepository, urls: EndpointUrlBuilder):
        self._endpoints = endpoints
        self._urls = urls

    @contract
    def get_for_any_response(self) -> Json:
        with open('/'.join((RESOURCE_PATH, 'schema/alfred/response.json'))) as file:
            return Json.from_raw(file.read())

    @contract
    def get_for_all_messages(self) -> Json:
        schemas = []
        for endpoint in self._endpoints.get_endpoints():
            request_schema = self.get_for_request(endpoint.name)
            if request_schema is not None:
                schemas.append(request_schema.data)
            response_schema = self.get_for_response(endpoint.name)
            if response_schema is not None:
                schemas.append(response_schema.data)
        return Json.from_data({
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'description': 'Any message.',
            'oneOf': schemas,
        })

    def get_url_for_response(self, endpoint_name: str) -> Optional[Json]:
        parameters = {
            'endpoint_name': endpoint_name
        }
        return self._urls.build('schemas.response', parameters)

    def get_for_request(self, endpoint_name: str) -> Optional[Json]:
        return self._endpoints.get_endpoint(
            endpoint_name).request_meta.get_json_schema()

    @contract
    def get_for_requests(self) -> Json:
        schemas = []
        for endpoint in self._endpoints.get_endpoints():
            request_schema = self.get_for_request(endpoint.name)
            if request_schema is not None:
                schemas.append(request_schema.data)
        return Json.from_data({
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'description': 'Any request.',
            'oneOf': schemas,
        })

    def get_for_response(self, endpoint_name: str) -> Optional[Json]:
        return self._endpoints.get_endpoint(
            endpoint_name).response_meta.get_json_schema()

    @contract
    def get_for_responses(self) -> Json:
        schemas = []
        for endpoint in self._endpoints.get_endpoints():
            response_schema = self.get_for_response(endpoint.name)
            if response_schema is not None:
                schemas.append(response_schema.data)
        return Json.from_data({
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'description': 'Any response.',
            'oneOf': schemas,
        })
