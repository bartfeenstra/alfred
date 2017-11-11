from typing import List, Optional

from flask import Flask, request as current_http_request
from flask.views import MethodView
from werkzeug.exceptions import NotAcceptable
from werkzeug.local import LocalProxy

from alfred.app import App
from alfred_http.endpoints import Error, \
    ErrorResponse, Endpoint, Request
from alfred_http.extension import HttpExtension


class FlaskApp(Flask):
    def __init__(self, extension_classes: Optional[List] = None):
        super().__init__('alfred')
        self._app = App()
        self._app.add_extension(HttpExtension)
        if extension_classes is not None:
            for extension_class in extension_classes:
                self._app.add_extension(extension_class)
        self._register_routes()

    @property
    def app(self):
        return self._app

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
