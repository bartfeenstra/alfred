from typing import List, Dict
from urllib.parse import urlparse

from contracts import contract
from flask import Flask, request as current_http_request, Response as FlaskHttpResponse
from flask.views import MethodView

from alfred.app import App
from alfred_http.endpoints import Error, \
    ErrorResponse, Endpoint, Request, NotAcceptableError, \
    UnsupportedMediaTypeError
from alfred_http.http import HttpRequest, HttpBody, HttpResponse


class EmptyFlaskHttpResponse(FlaskHttpResponse):
    """
    Provides a Flask HTTP response that is entirely empty by default.
    """
    default_mimetype = ''


@contract
def flask_to_alfred_http_request(flask_http_request, endpoint: Endpoint, kwargs: Dict) -> HttpRequest:
    content_type = flask_http_request.accept_mimetypes.best_match(
        endpoint.response_meta.get_content_types())
    request_charset = flask_http_request.mimetype_params.get(
        'charset')
    charset = request_charset if request_charset else 'utf-8'
    request_body_data = flask_http_request.get_data().decode(
        charset)
    request_body = HttpBody(request_body_data, content_type)
    request_parameters = {}
    for request_parameter in endpoint.request_meta.get_parameters():
        request_parameters[
            request_parameter.name] = request_parameter
    request_arguments = {}

    # Add query arguments.
    for query_name in flask_http_request.args:
        if query_name in request_parameters:
            query_value = flask_http_request.args.get(query_name)
            query_values = flask_http_request.args.getlist(
                query_name)
            # Use a single value, if it's expected and encountered.
            if request_parameters[
                    query_name].cardinality == 1 and [
                    query_value] == query_values:
                request_arguments[query_name] = query_value
            # In all other cases, pass on a list of the values.
            else:
                request_arguments[query_name] = query_values

    # Add URL path arguments.
    for kwarg_name, kwarg_value in kwargs.items():
        if kwarg_name in request_parameters:
            request_arguments[kwarg_name] = kwarg_value
    alfred_http_request = HttpRequest(body=request_body,
                                      arguments=request_arguments,
                                      headers=dict(
                                          flask_http_request.headers))

    return alfred_http_request


@contract
def alfred_to_flask_http_response(alfred_http_response: HttpResponse) -> FlaskHttpResponse:
    http_response = EmptyFlaskHttpResponse()
    http_response.status = str(alfred_http_response.status)
    for header_name, header_value in alfred_http_response.headers.items():
        http_response.headers.set(header_name, header_value)
    body = alfred_http_response.body
    if body:
        http_response.headers.set('Content-Type', body.content_type)
        http_response.set_data(body.content)
    return http_response


class FlaskApp(Flask):
    @contract
    def __init__(self, app: App):
        super().__init__('alfred')
        self._app = app
        self._register_routes()
        base_url = app.service('http', 'base_url')
        parsed_base_url = urlparse(base_url)
        self.config.update(PREFERRED_URL_SCHEME=parsed_base_url.scheme)
        self.config.update(SERVER_NAME=parsed_base_url.netloc)
        self.response_class = EmptyFlaskHttpResponse

    def _register_routes(self):
        endpoints = self._app.service('http', 'endpoints')

        # Collect endpoints per route.
        route_endpoints = {}
        for endpoint in endpoints.get_endpoints():
            route_endpoints.setdefault(endpoint.path, [])
            route_endpoints[endpoint.path].append(endpoint)

        # Register the routes.
        for path, endpoints in route_endpoints.items():
            route_name = path
            path = path.replace('{', '<').replace('}', '>')
            self.add_url_rule(path, endpoint=route_name,
                              view_func=EndpointView.as_view(endpoints[0].path,
                                                             self._app,
                                                             endpoints))


class EndpointView(MethodView):
    @contract
    def __init__(self, app: App, endpoints: List):
        for endpoint in endpoints:
            setattr(self, endpoint.request_meta.method.lower(),
                    self._build_view(app, endpoint))

    @staticmethod
    @contract
    def _build_view(app: App, endpoint: Endpoint):
        def _view(**kwargs):
            try:
                # Check we can produce the requested content type.
                content_type = current_http_request.accept_mimetypes.best_match(
                    endpoint.response_meta.get_content_types())
                if content_type is None:
                    raise NotAcceptableError()

                # Check the request consumes the provided content type.
                if current_http_request.mimetype not in endpoint.request_meta.get_content_types():
                    raise UnsupportedMediaTypeError()

                alfred_http_request = flask_to_alfred_http_request(
                    current_http_request, endpoint, kwargs)

                # Build the API request.
                alfred_request = endpoint.request_meta.from_http_request(
                    alfred_http_request)
                assert isinstance(alfred_request, Request)

                # Handle the API request, converting it to an API response.
                alfred_response = endpoint.handle(alfred_request)

                # Build the Alfred HTTP response.
                alfred_http_response = endpoint.response_meta.to_http_response(
                    alfred_response,
                    content_type)
                assert isinstance(alfred_http_response, HttpResponse)

                return alfred_to_flask_http_response(alfred_http_response)

            except Error as e:
                alfred_response = ErrorResponse().with_error(e)
                metas = app.service('http', 'error_response_metas').get_metas()
                metas_by_content_type = {}
                for meta in metas:
                    for content_type in meta.get_content_types():
                        metas_by_content_type.setdefault(content_type, [])
                        metas_by_content_type[content_type].append(meta)
                empty_metas = metas_by_content_type['']
                del metas_by_content_type['']

                # Check we can produce the requested content type.
                content_type = current_http_request.accept_mimetypes.best_match(
                    metas_by_content_type.keys())
                # Fall back to not including any content at all.
                if content_type is None:
                    content_type = ''
                    meta = empty_metas[0]
                else:
                    meta = metas_by_content_type[content_type][0]

                alfred_http_response = meta.to_http_response(
                    alfred_response, content_type)

                return alfred_to_flask_http_response(alfred_http_response)

        return _view
