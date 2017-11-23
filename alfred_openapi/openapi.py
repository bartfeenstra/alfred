from apispec import APISpec
from contracts import contract
from flask import request

from alfred_http.endpoints import EndpointRepository, EndpointUrlBuilder
from alfred_rest.endpoints import JsonMessageMeta


class OpenApi:
    @contract
    def __init__(self, endpoints: EndpointRepository, urls: EndpointUrlBuilder):
        self._endpoints = endpoints
        self._urls = urls

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

            if isinstance(endpoint.request_meta, JsonMessageMeta):
                operation['parameters'] = [
                    {
                        'name': 'body',
                        'description': 'The HTTP request body.',
                        'in': 'body',
                        'required': True,
                        'schema': {
                            '$ref': '%s#/definitions/request/%s' % (self._urls.build('schema'), endpoint.request_meta.name),
                        },
                    },
                ]

            if isinstance(endpoint.response_meta, JsonMessageMeta):
                operation['responses'][200]['schema'] = {
                    '$ref': '%s#/definitions/response/%s' % (self._urls.build('schema'), endpoint.response_meta.name),
                }

            paths_operations.setdefault(endpoint.path, {})
            paths_operations[endpoint.path].setdefault(method, {})
            paths_operations[endpoint.path][method] = operation

        for path, operations in paths_operations.items():
            spec.add_path(path, operations)
        return spec
