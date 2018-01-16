from unittest import TestCase

from alfred.app import App, Extension, ExtensionNotFound, ServiceNotFound, \
    RecursiveServiceDependency


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
