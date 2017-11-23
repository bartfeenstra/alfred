from flask_cors import CORS

from alfred.app import Extension
from alfred.extension import CoreExtension
from alfred_http.endpoints import NestedEndpointRepository, EndpointUrlBuilder
from alfred_http.flask.app import FlaskApp


class HttpExtension(Extension):
    @staticmethod
    def name():
        return 'http'

    @staticmethod
    def dependencies():
        return [CoreExtension]

    @Extension.service()
    def _endpoints(self):
        endpoints = NestedEndpointRepository()
        for tagged_endpoints in self._app.services(tag='http_endpoints'):
            endpoints.add_endpoints(tagged_endpoints)
        return endpoints

    @Extension.service()
    def base_url(self):
        # @todo Make this configurable.
        return 'http://127.0.0.1:5000'

    @Extension.service()
    def flask(self):
        flask = FlaskApp(self._app)
        CORS(flask)
        return flask

    @Extension.service()
    def _urls(self):
        return EndpointUrlBuilder(self._app.service('http', 'endpoints'))
