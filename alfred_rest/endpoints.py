import abc
import json

from contracts import contract
from requests import HTTPError

from alfred.app import Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import Endpoint, EndpointUrlBuilder, \
    EndpointRepository, \
    MessageMeta, \
    Response, SuccessResponse, SuccessResponseMeta, \
    NonConfigurableGetRequestMeta, NonConfigurableRequest
from alfred_rest.json import Json, get_schema


class JsonMessageMeta(MessageMeta):
    def get_content_types(self):
        return ['application/json']

    @abc.abstractmethod
    @contract
    def get_json_schema(self) -> Json:
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
        data = self.to_http_response_json_data(response, content_type).data
        if '$schema' not in data:
            data['$schema'] = '%s#definitions/response/%s' % (self._urls.build('schema'), self.name)
        http_response.set_data(json.dumps(data))

        return http_response

    @abc.abstractmethod
    @contract
    def to_http_response_json_data(self, response: Response,
                                   content_type: str) -> Json:
        pass


class JsonSchemaResponse(SuccessResponse):
    @contract
    def __init__(self, schema: Json):
        super().__init__()
        self._schema = schema

    @property
    @contract
    def schema(self) -> Json:
        return self._schema


class JsonSchemaResponseMeta(JsonResponseMeta, AppAwareFactory):
    @contract
    def __init__(self, urls: EndpointUrlBuilder):
        super().__init__('schema', urls)

    @classmethod
    def from_app(cls, app):
        return cls(app.service('http', 'urls'))

    def get_content_types(self):
        return ['application/schema+json']

    def to_http_response(self, response, content_type):
        http_response = super().to_http_response(response, content_type)
        http_response.status = '200'
        return http_response

    def to_http_response_json_data(self, response, content_type):
        assert isinstance(response, JsonSchemaResponse)
        return response.schema

    def get_json_schema(self):
        return Json.from_data({})
        # @todoReDoc fails on these references somehow. Find out why, and fix it.
        return Json.from_data({
            '$ref': self._urls.build('external-schema-json-schema'),
            'description': 'A JSON Schema.',
        })


class JsonSchemaEndpoint(Endpoint, AppAwareFactory):
    NAME = 'schema'

    @contract
    def __init__(self, factory: Factory, endpoints: EndpointRepository):
        super().__init__(factory, self.NAME,
                         '/about/json/schema',
                         NonConfigurableGetRequestMeta,
                         JsonSchemaResponseMeta)
        self._endpoints = endpoints

    @classmethod
    def from_app(cls, app):
        return cls(app.factory, app.service('http', 'endpoints'))

    def handle(self, request):
        assert isinstance(request, NonConfigurableRequest)
        schema = {
            'definitions': {
                'request': {},
                'response': {},
            },
        }
        for request_meta in self._endpoints.get_request_metas():
            if isinstance(request_meta, JsonMessageMeta):
                schema['definitions']['request'][request_meta.name] = request_meta.get_json_schema().data
        for response_meta in self._endpoints.get_response_metas():
            if isinstance(response_meta, JsonMessageMeta):
                schema['definitions']['response'][response_meta.name] = response_meta.get_json_schema().data
        return JsonSchemaResponse(Json.from_data(schema))


class ExternalJsonSchemaEndpoint(Endpoint, AppAwareFactory):
    """
    Provides an endpoint that proxies an external JSON Schema. This circumvents
    Cross-Origin Resource Sharing (CORS) problems, by not requiring API clients
    to load external resources themselves, and allows us to fix incorrect
    headers, such as Content-Type.
    """
    @contract
    def __init__(self, factory: Factory, name: str, url: str):
        super().__init__(factory, 'external-schema-%s' % name,
                         '/about/json/external-schema/%s' % name,
                         NonConfigurableGetRequestMeta,
                         JsonSchemaResponseMeta)
        self._url = url
        self._schema = None

    @classmethod
    def from_app(cls, app):
        return cls(app.factory)

    def handle(self, request):
        assert isinstance(request, NonConfigurableRequest)
        if self._schema is None:
            try:
                self._schema = get_schema(self._url)
            except HTTPError:
                # @todo We have no error handling yet!
                # @todo Make ErrorResponse work.
                # @todo Log these errors.
                pass

        return JsonSchemaResponse(self._schema)


@contract
def build_external_schema_endpoint(name: str, url: str) -> type:
    class _Endpoint(ExternalJsonSchemaEndpoint):
        def __init__(self, factory):
            super().__init__(factory, name, url)
    return _Endpoint
