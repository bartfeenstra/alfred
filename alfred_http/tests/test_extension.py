from unittest import TestCase

from contracts import contract

from alfred.app import App, Extension, Factory
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import EndpointRepository, EndpointUrlBuilder, \
    EndpointFactoryRepository, Endpoint, SuccessResponseMeta, \
    NonConfigurableRequestMeta
from alfred_http.extension import HttpExtension


class HttpExtensionTest(TestCase):
    class TestEndpoint(Endpoint, AppAwareFactory):
        @contract
        def __init__(self, factory: Factory):
            super().__init__(factory, 'http_test', 'http/test',
                             NonConfigurableRequestMeta, SuccessResponseMeta)

        @classmethod
        def from_app(cls, app):
            return cls(app.factory)

    class EndpointProvidingExtension(Extension):
        @staticmethod
        def dependencies():
            return [HttpExtension]

        @staticmethod
        def name():
            return 'http_test'

        @Extension.service(tags=('http_endpoints',))
        def _endpoints(self):
            return EndpointFactoryRepository(self._app.factory, [
                HttpExtensionTest.TestEndpoint
            ])

    def test_endpoints(self):
        app = App()
        app.add_extension(self.EndpointProvidingExtension)
        endpoints = app.service('http', 'endpoints')
        self.assertIsInstance(endpoints, EndpointRepository)

    def test_urls(self):
        app = App()
        app.add_extension(HttpExtension)
        urls = app.service('http', 'urls')
        self.assertIsInstance(urls, EndpointUrlBuilder)
