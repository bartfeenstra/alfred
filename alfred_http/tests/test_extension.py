from unittest import TestCase

from contracts import contract

from alfred.app import App, Extension, Factory
from alfred_http.endpoints import EndpointRepository, EndpointUrlBuilder, \
    EndpointFactoryRepository, Endpoint, SuccessResponseMeta, \
    NonConfigurableRequestMeta
from alfred_http.extension import HttpExtension


class HttpExtensionTest(TestCase):
    class TestEndpoint(Endpoint):
        @contract
        def __init__(self, factory: Factory):
            super().__init__(factory, 'http_test', 'http/test',
                             NonConfigurableRequestMeta, SuccessResponseMeta)

    class EndpointProvidingExtension(Extension):
        @staticmethod
        def dependencies():
            return [HttpExtension]

        @staticmethod
        def name():
            return 'http_test'

        @Extension.service(tags=('endpoints',))
        def _endpoints(self):
            return EndpointFactoryRepository([
                HttpExtensionTest.TestEndpoint
            ])

    def test_factories(self):
        app = App()
        app.add_extension(self.EndpointProvidingExtension)

        endpoints = app.service('http', 'endpoints')
        self.assertIsInstance(endpoints, EndpointRepository)
        self.skipTest()
        # print(endpoints.get_endpoints())

        urls = app.service('http', 'urls')
        self.assertIsInstance(urls, EndpointUrlBuilder)
