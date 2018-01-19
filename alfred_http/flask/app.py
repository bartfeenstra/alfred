from typing import List, Dict, Iterable
from urllib.parse import urlparse

from contracts import contract
from flask import Flask, request as current_http_request, \
    Response as FlaskHttpResponse
from flask.views import MethodView
from werkzeug.datastructures import MIMEAccept

from alfred.app import App
from alfred_http.endpoints import Error, \
    ErrorResponse, Endpoint, Request, NotAcceptableError, \
    ResponseType, ErrorResponseType
from alfred_http.http import HttpRequest, HttpBody, HttpResponse


class EmptyFlaskHttpResponse(FlaskHttpResponse):
    """
    Provides a Flask HTTP response that is entirely empty by default.
    """
    default_mimetype = ''


@contract
def flask_to_alfred_http_request(flask_http_request, endpoint: Endpoint,
                                 kwargs: Dict) -> HttpRequest:
    request_charset = flask_http_request.mimetype_params.get(
        'charset')
    charset = request_charset if request_charset else 'utf-8'
    request_body_data = flask_http_request.get_data().decode(
        charset)
    request_body = HttpBody(request_body_data, current_http_request.mimetype)

    request_arguments = {}
    for parameter in endpoint.request_type.get_parameters():
        # Add URL path arguments.
        if parameter.required:
            request_arguments[parameter.name] = kwargs[parameter.name]

        # Add query arguments.
        else:
            query_value = flask_http_request.args.get(parameter.name)
            query_values = flask_http_request.args.getlist(
                parameter.name)
            # Use a single value, if it's expected and encountered.
            if parameter.cardinality == 1 and [query_value] == query_values:
                request_arguments[parameter.name] = query_value
            # In all other cases, pass on a list of the values.
            else:
                request_arguments[parameter.name] = query_values

    alfred_http_request = HttpRequest(body=request_body,
                                      arguments=request_arguments,
                                      headers=dict(
                                          flask_http_request.headers))

    return alfred_http_request


@contract
def alfred_to_flask_http_response(
        alfred_http_response: HttpResponse) -> FlaskHttpResponse:
    http_response = EmptyFlaskHttpResponse()
    http_response.status = str(alfred_http_response.status)
    for header_name, header_value in alfred_http_response.headers.items():
        http_response.headers.set(header_name, header_value)
    body = alfred_http_response.body
    if body:
        http_response.headers.set('Content-Type', body.content_type)
        http_response.set_data(body.content)
    return http_response


@contract
def validate_accept_for_response_type(response_type: ResponseType,
                                      accept_headers: MIMEAccept):
    produced_content_types = []
    for payload_type in response_type.get_payload_types():
        produced_content_types += payload_type.get_content_types()
    return validate_accept(produced_content_types, accept_headers)


@contract
def validate_accept(produced_content_types: Iterable,
                    accept_headers: MIMEAccept):
    if not len(accept_headers):
        accept_headers = MIMEAccept([('*/*', 1)])

    # Flask does not like empty content types, but we use them.
    content_type = accept_headers.best_match(
        filter(lambda x: x != '', produced_content_types))
    if content_type is None:
        if '*/*' in accept_headers and '' in produced_content_types:
            return ''
        raise NotAcceptableError(
            description='This endpoint only returns one of the following content types: %s' % ', '.join(
                produced_content_types))
    return content_type


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
            methods = list(map(lambda x: x.request_type.method, endpoints))
            self.add_url_rule(path, endpoint=route_name,
                              view_func=EndpointView.as_view(endpoints[0].path,
                                                             self._app,
                                                             endpoints),
                              methods=methods)


class EndpointView(MethodView):
    @contract
    def __init__(self, app: App, endpoints: List):
        for endpoint in endpoints:
            setattr(self, endpoint.request_type.method.lower(),
                    self._build_view(app, endpoint))

    @staticmethod
    @contract
    def _build_view(app: App, endpoint: Endpoint):
        def _view(**kwargs):
            try:
                content_type = validate_accept_for_response_type(
                    endpoint.response_type,
                    current_http_request.accept_mimetypes)

                alfred_http_request = flask_to_alfred_http_request(
                    current_http_request, endpoint, kwargs)

                # Build the API request.
                alfred_request = endpoint.request_type.from_http_request(
                    alfred_http_request)
                assert isinstance(alfred_request, Request)

                # Handle the API request, converting it to an API response.
                alfred_response = endpoint.handle(alfred_request)

                # Build the Alfred HTTP response.
                alfred_http_response = endpoint.response_type.to_http_response(
                    alfred_response, content_type)

                return alfred_to_flask_http_response(alfred_http_response)

            except Error as e:
                alfred_response = ErrorResponse().with_error(e)

                error_response_type = ErrorResponseType()

                try:
                    content_type = validate_accept_for_response_type(
                        error_response_type,
                        current_http_request.accept_mimetypes)
                except NotAcceptableError:
                    # We know there is a payload type that outputs no content.
                    content_type = ''

                alfred_http_response = error_response_type.to_http_response(
                    alfred_response, content_type)

                return alfred_to_flask_http_response(alfred_http_response)

        return _view
