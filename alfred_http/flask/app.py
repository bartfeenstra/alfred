from typing import List, Optional

from flask import Flask, request as current_http_request_proxy
from flask.views import MethodView
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

    def _register_routes(self):
        endpoints = self._app.service('core', 'endpoint_repository')
        route_endpoints = {}
        for endpoint in endpoints.get_endpoints():
            route_endpoints.setdefault(endpoint.path, [])
            route_endpoints[endpoint.path].append(endpoint)
        for path, endpoints in route_endpoints.items():
            self.add_url_rule(path,
                              view_func=EndpointView.as_view(endpoints[0].path,
                                                             endpoints))


class EndpointView(MethodView):
    def __init__(self, endpoints: List):
        for endpoint in endpoints:
            setattr(self, endpoint.method.lower(), self._build_view(endpoint))

    @staticmethod
    def _build_view(endpoint: Endpoint):
        def _view(**kwargs):
            try:
                # Because Werkzeug uses duck-typed proxies, we access a
                # protected method to get the real request, so it passes our
                # type checks.
                if isinstance(current_http_request_proxy, LocalProxy):
                    current_http_request = current_http_request_proxy._get_current_object()  # noqa: E501
                else:
                    current_http_request = current_http_request_proxy

                alfred_request = endpoint.request_meta.from_http_request(
                    current_http_request, kwargs)
                assert isinstance(alfred_request, Request)
                alfred_response = endpoint.handle(alfred_request)
            except Error as e:
                alfred_response = ErrorResponse().with_error(e)

            return endpoint.response_meta.to_http_response(alfred_response)

        return _view
