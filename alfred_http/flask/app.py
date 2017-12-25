from typing import List
from urllib.parse import urlparse

from contracts import contract
from flask import Flask, request as current_http_request
from flask.views import MethodView
from werkzeug.local import LocalProxy

from alfred.app import App
from alfred_http.endpoints import Error, \
    ErrorResponse, Endpoint, Request, NotAcceptableError, \
    UnsupportedMediaTypeError


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
                return endpoint.response_meta.to_http_response(alfred_response,
                                                               content_type)
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

                return meta.to_http_response(alfred_response, content_type)

        return _view
