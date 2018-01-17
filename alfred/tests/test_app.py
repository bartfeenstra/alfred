from unittest import TestCase

from werkzeug.datastructures import MIMEAccept

from alfred.app import App, Extension, ExtensionNotFound, ServiceNotFound, \
    RecursiveServiceDependency
from alfred_http.endpoints import NotAcceptableError
from alfred_http.flask.app import validate_accept


class AppTest(TestCase):
    class TestExtension(Extension):
        @staticmethod
        def name():
            return 'test'

        @Extension.service()
        def _foo(self):
            return App.current.service('test', 'bar')

        @Extension.service()
        def _bar(self):
            return App.current.service('test', 'foo')

    def _without_parameters(self):
        return 'without'

    def test_service_inifite_loop(self):
        sut = App()
        sut.add_extension(self.TestExtension)
        with sut:
            with self.assertRaises(RecursiveServiceDependency):
                sut.service('test', 'foo')

    def testServiceWithNonExistentExtension(self):
        sut = App()
        with sut:
            with self.assertRaises(ExtensionNotFound):
                sut.service('i_do_not_exist', 'factory')

    def testServiceWithNonExistentService(self):
        sut = App()
        with sut:
            sut.add_extension(self.TestExtension)
            with self.assertRaises(ServiceNotFound):
                sut.service('test', 'i_do_not_exist')


class ValidateAcceptTest(TestCase):
    def testAcceptsNoneProducesNone(self):
        accept_headers = MIMEAccept([])
        produces = []
        with self.assertRaises(NotAcceptableError):
            validate_accept(produces, accept_headers)

    def testAcceptsAnyProducesNone(self):
        accept_headers = MIMEAccept([('*/*', 1)])
        produces = []
        with self.assertRaises(NotAcceptableError):
            validate_accept(produces, accept_headers)

    def testAcceptsNoneProducesEmpty(self):
        accept_headers = MIMEAccept([])
        produces = ['']
        self.assertEquals(validate_accept(produces, accept_headers), '')

    def testAcceptsAnyProducesEmpty(self):
        accept_headers = MIMEAccept([('*/*', 1)])
        produces = ['']
        self.assertEquals(validate_accept(produces, accept_headers), '')

    def testAcceptsAnyProducesOne(self):
        accept_headers = MIMEAccept([('*/*', 1)])
        produces = ['application/json']
        self.assertEquals(validate_accept(
            produces, accept_headers), 'application/json')

    def testAcceptsAnyProducesMany(self):
        accept_headers = MIMEAccept([('*/*', 1)])
        produces = ['application/json', 'text/html', 'text/xml']
        self.assertEquals(validate_accept(
            produces, accept_headers), 'application/json')

    def testAcceptsOneProducesOne(self):
        accept_headers = MIMEAccept([('application/json', 1)])
        produces = ['application/json']
        self.assertEquals(validate_accept(
            produces, accept_headers), 'application/json')
