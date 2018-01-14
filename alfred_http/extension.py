from flask_cors import CORS

from alfred.app import Extension, App
from alfred_http.endpoints import NestedEndpointRepository, EndpointUrlBuilder, \
    ErrorResponseTypeRepository, EmptyResponseType
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
    def _error_response_types(self):
        types = ErrorResponseTypeRepository()
        for tagged_type in App.current.services(tag='error_response_type'):
            types.add_type(tagged_type)
        return types

    @Extension.service(tags=('error_response_type',), weight=999)
    def _empty_error_response_type(self):
        return EmptyResponseType()
