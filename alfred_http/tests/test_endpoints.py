from unittest import TestCase
from unittest.mock import Mock

from contracts import contract
from werkzeug.routing import BuildError

from alfred.app import Factory, FactoryError, Extension
from alfred.extension import AppAwareFactory
from alfred_http.endpoints import EndpointFactoryRepository, Endpoint, \
    NestedEndpointRepository, EndpointRepository, NonConfigurableRequestMeta, \
    EndpointNotFound, \
    StaticEndpointRepository, SuccessResponseMeta
from alfred_http.extension import HttpExtension
from alfred_http.tests import HttpTestCase


class FooEndpoint(Endpoint):
    pass


class BarEndpoint(Endpoint):
    pass


class BazEndpoint(Endpoint):
    pass


class InstanceFactory(Factory):
    def __init__(self, instances):
        self._instances = instances

    def new(self, spec):
        if not isinstance(spec, type):
            raise FactoryError(
                'Can only use classes, but %s was given.' % spec)
        for instance in self._instances:
            if isinstance(instance, spec):
                return instance
        raise FactoryError('%s is not in %s' % (spec, self._instances))


def mock_endpoints():
    endpoint_foo = Mock(FooEndpoint)
    endpoint_bar = Mock(BarEndpoint)
    endpoint_baz = Mock(BazEndpoint)
    endpoint_foo.name = 'foo'
    endpoint_bar.name = 'bar'
    endpoint_baz.name = 'baz'
    return (endpoint_foo, endpoint_bar, endpoint_bar)


class StaticEndpointRepositoryTest(TestCase):
    def testGetEndpointWithExistingEndpoint(self):
        endpoint_foo, endpoint_bar, endpoint_baz = mock_endpoints()
        sut = StaticEndpointRepository([endpoint_foo,
                                        endpoint_bar,
                                        endpoint_baz])
        self.assertEquals(sut.get_endpoint('bar'), endpoint_bar)

    def testGetEndpointWithNonExistingEndpoint(self):
        endpoint_foo, endpoint_bar, endpoint_baz = mock_endpoints()
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
        endpoint_foo, endpoint_bar, endpoint_baz = mock_endpoints()
        sut = StaticEndpointRepository([endpoint_foo,
                                        endpoint_bar,
                                        endpoint_baz])
        self.assertSequenceEqual(sut.get_endpoints(),
                                 [endpoint_foo, endpoint_bar, endpoint_baz])

    def testGetEndpointsWithoutEndpoints(self):
        sut = StaticEndpointRepository([])
        self.assertSequenceEqual(sut.get_endpoints(), [])


class EndpointFactoryRepositoryTest(TestCase):
    def mock_factory(self):
        endpoints = mock_endpoints()
        factory = InstanceFactory(endpoints)
        return (factory, *endpoints)

    def testGetEndpointWithExistingEndpoint(self):
        factory, endpoint_foo, endpoint_bar, endpoint_baz = self.mock_factory()
        sut = EndpointFactoryRepository(factory,
                                        [endpoint_foo.__class__,
                                         endpoint_bar.__class__,
                                         endpoint_baz.__class__])
        self.assertIsInstance(sut.get_endpoint('bar'), endpoint_bar.__class__)

    def testGetEndpointWithNonExistingEndpoint(self):
        factory, endpoint_foo, endpoint_bar, endpoint_baz = self.mock_factory()
        sut = EndpointFactoryRepository(factory,
                                        [endpoint_foo.__class__,
                                         endpoint_bar.__class__,
                                         endpoint_baz.__class__])
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

    def testGetEndpointWithoutEndpoints(self):
        factory = InstanceFactory([])
        sut = EndpointFactoryRepository(factory, [])
        with self.assertRaises(EndpointNotFound):
            sut.get_endpoint('qux')

    def testGetEndpointsWithEndpoints(self):
        factory, endpoint_foo, endpoint_bar, endpoint_baz = self.mock_factory()
        sut = EndpointFactoryRepository(factory,
                                        [endpoint_foo.__class__,
                                         endpoint_bar.__class__,
                                         endpoint_baz.__class__])
        self.assertSequenceEqual(sut.get_endpoints(),
                                 [endpoint_foo, endpoint_bar, endpoint_baz])

    def testGetEndpointsWithoutEndpoints(self):
        factory = InstanceFactory([])
        sut = EndpointFactoryRepository(factory, [])
        self.assertSequenceEqual(sut.get_endpoints(), [])


class NestedEndpointRepositoryTest(TestCase):
    def mock_endpoints(self):
        endpoint_foo, endpoint_bar, endpoint_baz = mock_endpoints()

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
    class TestEndpoint(Endpoint, AppAwareFactory):
        @contract
        def __init__(self, factory: Factory):
            super().__init__(factory, 'http_test', '/http/test',
                             NonConfigurableRequestMeta, SuccessResponseMeta)

        @classmethod
        def from_app(cls, app):
            return cls(app.factory)

        def handle(self, request):
            pass

    class TestEndpointWithUrlPathParameters(Endpoint, AppAwareFactory):
        @contract
        def __init__(self, factory: Factory):
            super().__init__(factory, 'http_test_with_parameters', '/http/test/{foo}',
                             NonConfigurableRequestMeta, SuccessResponseMeta)

        @classmethod
        def from_app(cls, app):
            return cls(app.factory)

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
            return EndpointFactoryRepository(self._app.factory, [
                EndpointUrlBuilderTest.TestEndpoint,
                EndpointUrlBuilderTest.TestEndpointWithUrlPathParameters,
            ])

    def get_extension_classes(self):
        return super().get_extension_classes() + [self.EndpointProvidingExtension]

    def testBuildWithoutParameters(self):
        sut = self._app.service('http', 'urls')
        self.assertEquals(sut.build('http_test'),
                          'http://127.0.0.1:5000/http/test')

    def testBuildWithParameters(self):
        sut = self._app.service('http', 'urls')
        self.assertEquals(sut.build('http_test_with_parameters', {
            'foo': 'bar',
        }),
            'http://127.0.0.1:5000/http/test/bar')

    def testBuildWithMissingParameters(self):
        sut = self._app.service('http', 'urls')
        with self.assertRaises(BuildError):
            sut.build('http_test_with_parameters')

    def testBuildWithNonExistingEndpoint(self):
        sut = self._app.service('http', 'urls')
        with self.assertRaises(EndpointNotFound):
            sut.build('i_do_not_exist')
