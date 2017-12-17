import abc
import json
from typing import Dict, Iterable

from contracts import contract
from flask import Request as HttpRequest

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import Endpoint, EndpointUrlBuilder, \
    EndpointRepository, \
    MessageMeta, \
    Response, SuccessResponse, SuccessResponseMeta, \
    NonConfigurableGetRequestMeta, NonConfigurableRequest, RequestMeta, \
    Request, ErrorResponse, NotFoundError
from alfred_rest import base64_decodes
from alfred_rest.json import Rewriter, IdentifiableDataType, ListType, \
    SchemaRepository, SchemaNotFound


class ErrorType(IdentifiableDataType):
    def __init__(self):
        super().__init__({
            'title': 'An API error',
            'type': 'object',
            'properties': {
                'code': {
                    'title': 'The machine-readable error code.',
                    'type': 'string',
                },
                'title': {
                    'title': 'The human-readable error title.',
                    'type': 'string',
                },
            },
            'required': ['code', 'title'],
        }, 'error')

    def to_json(self, resource):
        return {
            'code': resource.code,
            'title': resource.title,
        }


class ErrorResponseType(IdentifiableDataType):
    def __init__(self):
        self._data_type = ListType(ErrorType())
        super().__init__({
            'title': 'Error response',
            'type': 'object',
            'properties': {
                'errors': self._data_type,
            },
            'required': ['errors'],
        }, 'error', 'response')

    def to_json(self, resource):
        assert isinstance(resource, ErrorResponse)
        return {
            'errors': self._data_type.to_json(resource.errors),
        }


class ResourceType(IdentifiableDataType):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['type'] = 'object'
        self.setdefault('properties', {})
        self.setdefault('required', [])
        self['properties'].update({
            'id': {
                'type': 'string',
            },
        })
        self['required'].append('id')


class JsonMessageMeta(MessageMeta):
    def get_content_types(self):
        return ['application/json']

    @abc.abstractmethod
    @contract
    def get_json_schema(self) -> Dict:
        pass


class JsonResponseMeta(SuccessResponseMeta, JsonMessageMeta):
    @contract
    def __init__(self, name: str, urls: EndpointUrlBuilder):
        super().__init__(name)
        self._urls = urls

    def to_http_response(self, response, content_type):
        http_response = super().to_http_response(response, content_type)
        # @todo Validate the JSON. But we can only do that once all children are done with this method....
        # @todo How do we do that?
        # @todo Maybe only when debug=True, though.
        # @todo Can this be moved to the parent class so we validate requests as well?
        data = self.to_json(response, content_type)
        http_response.set_data(json.dumps(data))

        return http_response

    @abc.abstractmethod
    @contract
    def to_json(self, response: Response, content_type: str):
        pass


class RestErrorResponseMeta(JsonResponseMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_type = ErrorResponseType()

    def to_json(self, response, content_type):
        return self._data_type.to_json(response)

    def get_json_schema(self):
        return self._data_type


class RestResponseMeta(RestErrorResponseMeta):
    def to_json(self, response, content_type):
        if isinstance(response, SuccessResponse):
            return self.to_success_json(response,
                                        content_type)
        return super().to_json(response, content_type)

    def get_json_schema(self):
        return {
            'anyOf': [
                super().get_json_schema(),
                self.get_success_json_schema(),
            ],
        }

    @abc.abstractmethod
    @contract
    def get_success_json_schema(self) -> Dict:
        pass

    @abc.abstractmethod
    @contract
    def to_success_json(self, response: Response,
                        content_type: str):
        pass


class RestResourcesResponseMeta(RestResponseMeta):
    def get_success_json_schema(self):
        return {
            'type': 'array',
            'items': {
                'type': self._get_resource_type()
            },
        }

    @abc.abstractmethod
    @contract
    def _get_resource_type(self) -> ResourceType:
        pass

    @abc.abstractmethod
    @contract
    def _get_resources(self) -> Iterable:
        pass

    def to_success_json(self, response, content_type):
        items = []
        for resource in self._get_resources():
            items.append(self._get_resource_type().to_json(resource))
        return items


class JsonSchemaResponse(SuccessResponse):
    @contract
    def __init__(self, schema: Dict):
        super().__init__()
        self._schema = schema

    @property
    @contract
    def schema(self) -> Dict:
        return self._schema


class JsonSchemaResponseMeta(RestResponseMeta, AppAwareFactory):
    NAME = 'schema'

    @contract
    def __init__(self, urls: EndpointUrlBuilder, rewriter: Rewriter):
        super().__init__(self.NAME, urls)
        self._rewriter = rewriter

    @classmethod
    def from_app(cls, app):
        return cls(app.service('http', 'urls'),
                   app.service('rest', 'json_schema_rewriter'))

    def get_content_types(self):
        return ['application/schema+json']

    def to_http_response(self, response, content_type):
        http_response = super().to_http_response(response, content_type)
        http_response.status = '200'
        return http_response

    def to_success_json(self, response, content_type):
        assert isinstance(response, JsonSchemaResponse)
        schema = response.schema
        self._rewriter.rewrite(schema)
        return schema

    def get_success_json_schema(self):
        return {
            '$ref': 'http://json-schema.org/draft-04/schema#',
            'description': 'A JSON Schema.',
        }


class JsonSchemaEndpoint(Endpoint, AppAwareFactory):
    NAME = 'schema'

    @contract
    def __init__(self, factory: Factory, endpoints: EndpointRepository,
                 urls: EndpointUrlBuilder):
        super().__init__(factory, self.NAME,
                         '/about/json/schema',
                         NonConfigurableGetRequestMeta,
                         JsonSchemaResponseMeta)
        self._endpoints = endpoints
        self._urls = urls

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'endpoints'),
                   app.service('http', 'urls'))

    def handle(self, request):
        assert isinstance(request, NonConfigurableRequest)
        schema = {
            'id': self._urls.build(self.name),
            '$schema': 'http://json-schema.org/draft-04/schema#',
            # Prevent most values from validating against the top-level schema.
            'enum': [None],
            'definitions': {
                'request': {},
                'response': {},
            },
        }
        for request_meta in self._endpoints.get_request_metas():
            if isinstance(request_meta, JsonMessageMeta):
                schema['definitions']['request'][
                    request_meta.name] = request_meta.get_json_schema(
                )
        for response_meta in self._endpoints.get_response_metas():
            if isinstance(response_meta, JsonMessageMeta):
                schema['definitions']['response'][
                    response_meta.name] = response_meta.get_json_schema(
                )
        return JsonSchemaResponse(schema)


class ExternalJsonSchemaRequestMeta(RequestMeta):
    NAME = 'external-schema'

    def __init__(self):
        super().__init__(self.NAME, 'GET')

    def from_http_request(self, http_request: HttpRequest,
                          parameters: Dict):
        return ExternalJsonSchemaRequest(base64_decodes(parameters['id']))

    def get_content_types(self):
        return []


class ExternalJsonSchemaRequest(Request):
    @contract
    def __init__(self, schema_url: str):
        self._schema_url = schema_url

    @property
    def schema_url(self):
        return self._schema_url


class ExternalJsonSchemaEndpoint(Endpoint, AppAwareFactory):
    """
    Provides an endpoint that proxies an external JSON Schema. This circumvents
    Cross-Origin Resource Sharing (CORS) problems, by not requiring API clients
    to load external resources themselves, and allows us to fix incorrect
    headers, such as Content-Type.

    The {id} parameter is the base64-encoded URL of the schema to load.
    """

    NAME = 'external-schema'

    @contract
    def __init__(self, factory: Factory, urls: EndpointUrlBuilder,
                 schemas: SchemaRepository):
        super().__init__(factory, self.NAME,
                         '/about/json/external-schema/{id}',
                         ExternalJsonSchemaRequestMeta,
                         JsonSchemaResponseMeta)
        self._urls = urls
        self._schemas = schemas

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'urls'),
                   app.service('rest', 'json_schemas'))

    def handle(self, request):
        assert isinstance(request, ExternalJsonSchemaRequest)
        schema_url = request.schema_url
        try:
            schema = self._schemas.get_schema(schema_url)
            return JsonSchemaResponse(schema)
        except SchemaNotFound:
            raise NotFoundError()
