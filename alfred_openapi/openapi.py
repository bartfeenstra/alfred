from apispec import APISpec
from contracts import contract

from alfred_http.endpoints import EndpointRepository
from alfred_http.schemas import SchemaRepository


class OpenApi:
    @contract
    def __init__(self, endpoints: EndpointRepository,
                 schemas: SchemaRepository):
        self._endpoints = endpoints
        self._schemas = schemas

    @contract
    def get(self) -> APISpec:
        # @todo How to determine the API version?
        return APISpec('Alfred', '0.0.0')
