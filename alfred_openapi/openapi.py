from apispec import APISpec
from contracts import contract
from flask import request

from alfred_http.endpoints import EndpointRepository


class OpenApi:
    @contract
    def __init__(self, endpoints: EndpointRepository):
        self._endpoints = endpoints

    @contract
    def get(self) -> APISpec:
        responses = {
            406: {
                'description': 'Returned if the request `Accept` header does not contain any content type produced by this endpoint.',
            },
            415: {
                'description': 'Returned if the request `Content-Type` header does not contain any content type consumed by this endpoint.',
            },
        }
        info = {
            'description': 'This document describes Alfred\'s HTTP API in the [OpenApi 2.0](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md) format.',
        }
        # @todo How to determine the API version?
        spec = APISpec('Alfred', '0.0.0', info=info, responses=responses,
                       host=request.host, schemes=[request.scheme])

        paths_operations = {}
        for endpoint in self._endpoints.get_endpoints():
            method = endpoint.request_meta.method.lower()

            operation = {
                'operationId': endpoint.name,
                'consumes': endpoint.request_meta.get_content_types(),
                'produces': endpoint.response_meta.get_content_types(),
                'responses': {
                    200: {
                        'description': 'A successful response.',
                    },
                    406: {
                        '$ref': '#/responses/406',
                    },
                    415: {
                        '$ref': '#/responses/415',
                    },
                },
            }

            # @todo ReDoc fails on $ref.
            # if isinstance(endpoint.response_meta, JsonResponseMeta):
            #     operation['responses'][200]['schema'] = endpoint.response_meta.get_json_schema().data

            paths_operations.setdefault(endpoint.path, {})
            paths_operations[endpoint.path].setdefault(method, {})
            paths_operations[endpoint.path][method] = operation

        for path, operations in paths_operations.items():
            spec.add_path(path, operations)
        return spec
