from flask_cors import CORS

from alfred.app import Extension, App
from alfred_http.endpoints import NestedEndpointRepository, EndpointUrlBuilder, \
    EmptyPayloadType
from alfred_http.flask.app import FlaskApp
from alfred_json.extension import JsonExtension


class HttpExtension(Extension):
    @staticmethod
    def name():
        return 'http'

    @staticmethod
    def dependencies():
        return [JsonExtension]

    @Extension.service()
    def _endpoints(self):
        endpoints = NestedEndpointRepository()
        for tagged_endpoints in App.current.services(tag='http_endpoints'):
            endpoints.add_endpoints(tagged_endpoints)
        return endpoints

    @Extension.service()
    def base_url(self):
        def _base_url():
            flask_app = App.current.service('http', 'flask')
            return '%s://%s' % (flask_app.config['PREFERRED_URL_SCHEME'], flask_app.config['SERVER_NAME'])
        return _base_url

    @Extension.service()
    def flask(self):
        flask = FlaskApp(App.current)
        CORS(flask)
        return flask

    @Extension.service()
    def _urls(self):
        return EndpointUrlBuilder(App.current.service('http', 'endpoints'))

    @Extension.service()
    def _error_response_payload_types(self):
        return App.current.services(tag='error_response_payload_type')

    @Extension.service(tags=('error_response_payload_type',))
    def _empty_error_response_payload_type(self):
        return EmptyPayloadType()
