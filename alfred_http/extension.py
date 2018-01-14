from flask_cors import CORS

from alfred.app import Extension, App
from alfred_http.endpoints import NestedEndpointRepository, EndpointUrlBuilder, \
    ErrorResponseMetaRepository, EmptyResponseMeta
from alfred_http.flask.app import FlaskApp


class HttpExtension(Extension):
    @staticmethod
    def name():
        return 'http'

    @Extension.service()
    def _endpoints(self):
        endpoints = NestedEndpointRepository()
        for tagged_endpoints in App.current.services(tag='http_endpoints'):
            endpoints.add_endpoints(tagged_endpoints)
        return endpoints

    @Extension.service()
    def base_url(self):
        # @todo Make this configurable.
        return 'http://127.0.0.1:5000'

    @Extension.service()
    def flask(self):
        flask = FlaskApp(App.current)
        CORS(flask)
        return flask

    @Extension.service()
    def _urls(self):
        return EndpointUrlBuilder(App.current.service('http', 'endpoints'))

    @Extension.service()
    def _error_response_metas(self):
        metas = ErrorResponseMetaRepository()
        for tagged_meta in App.current.services(tag='error_response_meta'):
            metas.add_meta(tagged_meta)
        return metas

    @Extension.service(tags=('error_response_meta',), weight=999)
    def _empty_error_response_meta(self):
        return EmptyResponseMeta()
