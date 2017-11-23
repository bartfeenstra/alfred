from typing import List
from urllib.parse import urlparse

from contracts import contract
from flask import Flask, request as current_http_request
from flask.views import MethodView
from werkzeug.exceptions import NotAcceptable
from werkzeug.local import LocalProxy

from alfred.app import App
from alfred_http.endpoints import Error, \
    ErrorResponse, Endpoint, Request


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

    def _register_routes(self):
        endpoints = self._app.service('http', 'endpoints')
        route_endpoints = {}
        for endpoint in endpoints.get_endpoints():
            route_endpoints.setdefault(endpoint.path, [])
            route_endpoints[endpoint.path].append(endpoint)
        for path, endpoints in route_endpoints.items():
            route_name = path
            path = path.replace('{', '<').replace('}', '>')
            self.add_url_rule(path, endpoint=route_name,
                              view_func=EndpointView.as_view(endpoints[0].path,
                                                             endpoints))


class EndpointView(MethodView):
    def __init__(self, endpoints: List):
        for endpoint in endpoints:
            setattr(self, endpoint.request_meta.method.lower(),
                    self._build_view(endpoint))

    @staticmethod
    def _build_view(endpoint: Endpoint):
        def _view(**kwargs):
            # Check we can deliver the right content type.
            content_type = current_http_request.accept_mimetypes.best_match(
                endpoint.response_meta.get_content_types())
            if content_type is None:
                raise NotAcceptable()

            try:
                alfred_request = endpoint.request_meta.from_http_request(
                    # Because Werkzeug uses duck-typed proxies, we access a
                    # protected method to get the real request, so it passes
                    # our type checks.
                    current_http_request._get_current_object() if isinstance(
                        current_http_request,
                        LocalProxy) else current_http_request,
                    kwargs)
                assert isinstance(alfred_request, Request)
                alfred_response = endpoint.handle(alfred_request)
            except Error as e:
                alfred_response = ErrorResponse().with_error(e)

            return endpoint.response_meta.to_http_response(alfred_response,
                                                           content_type)

        return _view
