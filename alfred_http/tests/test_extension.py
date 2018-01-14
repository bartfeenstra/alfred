from unittest import TestCase

from alfred.app import App, Extension
from alfred_http.endpoints import EndpointRepository, EndpointUrlBuilder, \
    Endpoint, StaticEndpointRepository, EmptyResponseMeta, SuccessResponse, \
    Request, \
    NonConfigurableGetRequestMeta
from alfred_http.extension import HttpExtension


class HttpExtensionTest(TestCase):
    class TestEndpoint(Endpoint):
        def __init__(self):
            super().__init__('http_test', 'http/test',
                             NonConfigurableGetRequestMeta(),
                             EmptyResponseMeta())

        def handle(self, request: Request):
            return SuccessResponse()

    class EndpointProvidingExtension(Extension):
        @staticmethod
        def dependencies():
            return [HttpExtension]

        @staticmethod
        def name():
            return 'http_test'

        @Extension.service(tags=('http_endpoints',))
        def _endpoints(self):
            return StaticEndpointRepository([
                HttpExtensionTest.TestEndpoint(),
            ])

    def test_endpoints(self):
        app = App()
        with app:
            app.add_extension(self.EndpointProvidingExtension)
            endpoints = app.service('http', 'endpoints')
            self.assertIsInstance(endpoints, EndpointRepository)

    def test_urls(self):
        app = App()
        with app:
            app.add_extension(HttpExtension)
            urls = app.service('http', 'urls')
            self.assertIsInstance(urls, EndpointUrlBuilder)
