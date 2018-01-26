from unittest import TestCase
from unittest.mock import Mock

from werkzeug.routing import BuildError

from alfred.app import Extension
from alfred_http.endpoints import Endpoint, \
    NestedEndpointRepository, EndpointRepository, EndpointNotFound, \
    StaticEndpointRepository, EndpointFactoryRepository, \
    NonConfigurableGetRequestType, EmptyResponseType, SuccessResponse, Request
from alfred_http.extension import HttpExtension
from alfred_http.tests import HttpTestCase


class FooEndpoint(Endpoint):
    def __init__(self):
        super().__init__('foo', '/foo', NonConfigurableGetRequestType(), EmptyResponseType())

    def handle(self, request: Request):
        return SuccessResponse()


class BarEndpoint(Endpoint):
    def __init__(self):
        super().__init__('bar', '/bar', NonConfigurableGetRequestType(), EmptyResponseType())

    def handle(self, request: Request):
        return SuccessResponse()


class BazEndpoint(Endpoint):
    def __init__(self):
        super().__init__('baz', '/baz', NonConfigurableGetRequestType(), EmptyResponseType())

    def handle(self, request: Request):
        return SuccessResponse()


class StaticEndpointRepositoryTest(TestCase):
    def testGetEndpointWithExistingEndpoint(self):
        endpoint_foo = FooEndpoint()
        endpoint_bar = BarEndpoint()
        endpoint_baz = BazEndpoint()
        sut = StaticEndpointRepository([endpoint_foo,
                                        endpoint_bar,
                                        endpoint_baz])
        self.assertEquals(sut.get_endpoint('bar'), endpoint_bar)

    def testGetEndpointWithNonExistingEndpoint(self):
        endpoint_foo = FooEndpoint()
        endpoint_bar = BarEndpoint()
        endpoint_baz = BazEndpoint()
        sut = StaticEndpointRepository([endpoint_foo,
                                        endpoint_bar,
                                        endpoint_baz])
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

    def testGetEndpointWithoutEndpoints(self):
        sut = StaticEndpointRepository([])
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

    def testGetEndpointsWithEndpoints(self):
        endpoint_foo = FooEndpoint()
        endpoint_bar = BarEndpoint()
        endpoint_baz = BazEndpoint()
        sut = StaticEndpointRepository([endpoint_foo,
                                        endpoint_bar,
                                        endpoint_baz])
        self.assertSequenceEqual(sut.get_endpoints(),
                                 [endpoint_foo, endpoint_bar, endpoint_baz])

    def testGetEndpointsWithoutEndpoints(self):
        sut = StaticEndpointRepository([])
        self.assertSequenceEqual(sut.get_endpoints(), [])


class EndpointFactoryRepositoryTest(TestCase):
    def testGetEndpointWithExistingEndpoint(self):
        endpoint_foo = FooEndpoint()
        endpoint_bar = BarEndpoint()
        endpoint_baz = BazEndpoint()
        sut = EndpointFactoryRepository([endpoint_foo.__class__,
                                         endpoint_bar.__class__,
                                         endpoint_baz.__class__])
        self.assertIsInstance(sut.get_endpoint('bar'), endpoint_bar.__class__)

    def testGetEndpointWithNonExistingEndpoint(self):
        endpoint_foo = FooEndpoint()
        endpoint_bar = BarEndpoint()
        endpoint_baz = BazEndpoint()
        sut = EndpointFactoryRepository([endpoint_foo.__class__,
                                         endpoint_bar.__class__,
                                         endpoint_baz.__class__])
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

    def testGetEndpointWithoutEndpoints(self):
        sut = EndpointFactoryRepository([])
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

    def testGetEndpointsWithEndpoints(self):
        sut = EndpointFactoryRepository(
            [FooEndpoint, BarEndpoint, BazEndpoint])
        endpoints = sut.get_endpoints()
        self.assertEquals(len(endpoints), 3)
        self.assertIsInstance(endpoints[1], BarEndpoint)
        self.assertIsInstance(endpoints[0], FooEndpoint)
        self.assertIsInstance(endpoints[2], BazEndpoint)

    def testGetEndpointsWithoutEndpoints(self):
        sut = EndpointFactoryRepository([])
        self.assertSequenceEqual(sut.get_endpoints(), [])


class NestedEndpointRepositoryTest(TestCase):
    def mock_endpoints(self):
        endpoint_foo = FooEndpoint()
        endpoint_bar = BarEndpoint()
        endpoint_baz = BazEndpoint()

        endpoints_baz_foo = Mock(EndpointRepository)
        endpoints_baz_foo.get_endpoints = lambda: [endpoint_baz, endpoint_foo]

        endpoints_bar = Mock(EndpointRepository)
        endpoints_bar.get_endpoints = lambda: [endpoint_bar]

        return (endpoints_baz_foo, endpoints_bar), (
            endpoint_baz, endpoint_foo, endpoint_bar)

    def testGetEndpointWithExistingEndpoint(self):
        repositories, endpoints = self.mock_endpoints()
        sut = NestedEndpointRepository()
        for repository in repositories:
            sut.add_endpoints(repository)
        self.assertEquals(sut.get_endpoint('bar'), endpoints[2])

    def testGetEndpointWithNonExistingEndpoint(self):
        repositories, endpoints = self.mock_endpoints()
        sut = NestedEndpointRepository()
        for repository in repositories:
            sut.add_endpoints(repository)
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

    def testGetEndpointWithoutEndpoints(self):
        sut = NestedEndpointRepository()
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

        # Add nested repositories, and assert the endpoint is available now.
        repositories, endpoints = self.mock_endpoints()
        for repository in repositories:
            sut.add_endpoints(repository)
        self.assertEquals(sut.get_endpoint('bar'), endpoints[2])

    def testGetEndpointsWithEndpoints(self):
        repositories, endpoints = self.mock_endpoints()
        sut = NestedEndpointRepository()
        for repository in repositories:
            sut.add_endpoints(repository)
        self.assertSequenceEqual(sut.get_endpoints(),
                                 endpoints)

    def testGetEndpointsWithoutEndpoints(self):
        sut = NestedEndpointRepository()
        self.assertSequenceEqual(sut.get_endpoints(), [])

        # Add nested repositories, and assert the endpoints are available now.
        repositories, endpoints = self.mock_endpoints()
        for repository in repositories:
            sut.add_endpoints(repository)
        self.assertSequenceEqual(sut.get_endpoints(),
                                 endpoints)


class EndpointUrlBuilderTest(HttpTestCase):
    class TestEndpoint(Endpoint):
        def __init__(self):
            super().__init__('http_test', '/http/test',
                             NonConfigurableGetRequestType(),
                             EmptyResponseType())

        def handle(self, request):
            pass

    class TestEndpointWithUrlPathParameters(Endpoint):
        def __init__(self):
            super().__init__('http_test_with_parameters',
                             '/http/test/{foo}',
                             NonConfigurableGetRequestType(),
                             EmptyResponseType())

        def handle(self, request):
            pass

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
                EndpointUrlBuilderTest.TestEndpoint(),
                EndpointUrlBuilderTest.TestEndpointWithUrlPathParameters(),
            ])

    def get_extension_classes(self):
        return super().get_extension_classes() + [
            self.EndpointProvidingExtension]

    def testBuildWithoutParameters(self):
        sut = self._app.service('http', 'urls')
        self.assertEquals(sut.build('http_test'),
                          'http://alfred.local/http/test')

    def testBuildWithParameters(self):
        sut = self._app.service('http', 'urls')
        self.assertEquals(sut.build('http_test_with_parameters', {
            'foo': 'bar',
        }),
            'http://alfred.local/http/test/bar')

    def testBuildWithMissingParameters(self):
        sut = self._app.service('http', 'urls')
        with self.assertRaises(BuildError):
            sut.build('http_test_with_parameters')

    def testBuildWithNonExistingEndpoint(self):
        sut = self._app.service('http', 'urls')
        with self.assertRaises(EndpointNotFound):
            sut.build('i_do_not_exist')
