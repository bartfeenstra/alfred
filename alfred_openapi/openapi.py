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
        return APISpec('Alfred', '0.0.0')
