from unittest import TestCase

from alfred.app import ClassFactory, FactoryError, CallableFactory, \
    MultipleFactories, App, Factory, Extension, ExtensionNotFound, \
    ServiceNotFound


class CallableFactoryTest(TestCase):
    def _without_parameters(self):
        return 'without'

    def _with_parameters(self, required):
        pass

    def test_success(self):
        sut = CallableFactory()
        instance = sut.new(self._without_parameters)
        self.assertEqual(instance, 'without')

    def test_error(self):
        sut = CallableFactory()
        with self.assertRaises(FactoryError):
            sut.new(self._with_parameters)


class ClassFactoryTest(TestCase):
    class WithoutConstructorParameters:
        pass

    class WithConstructorParameters:
        def __init__(self, required):
            pass

    def test_success(self):
        sut = ClassFactory()
        instance = sut.new(self.WithoutConstructorParameters)
        self.assertIsInstance(instance, self.WithoutConstructorParameters)

    def test_error(self):
        sut = ClassFactory()
        with self.assertRaises(FactoryError):
            sut.new(self.WithConstructorParameters)


class MultipleFactoriesTest(TestCase):
    class WithoutConstructorParameters:
        pass

    class WithConstructorParameters:
        def __init__(self, required):
            pass

    def _without_parameters(self):
        return 'without'

    def _with_parameters(self, required):
        pass

    def test_without_factories(self):
        sut = MultipleFactories()
        with self.assertRaises(FactoryError):
            sut.new(None)

    def test_success_with_first_factory(self):
        sut = MultipleFactories()
        sut.set_factories((
            CallableFactory(),
            ClassFactory(),
        ))
        instance = sut.new(self._without_parameters)
        self.assertEqual(instance, 'without')

    def test_success_with_last_factory(self):
        sut = MultipleFactories()
        sut.set_factories((
            CallableFactory(),
            ClassFactory(),
        ))
        instance = sut.new(self.WithoutConstructorParameters)
        self.assertIsInstance(instance, self.WithoutConstructorParameters)

    def test_error_for_all_factories(self):
        sut = ClassFactory()
        with self.assertRaises(FactoryError):
            sut.new(self._with_parameters)
        with self.assertRaises(FactoryError):
            sut.new(self.WithConstructorParameters)


class AppTest(TestCase):
    class TestExtension(Extension):
        @staticmethod
        def name():
            return 'test'

        @Extension.service()
        def _foo(self):
            return self._app.service('test', 'bar')

        @Extension.service()
        def _bar(self):
            return self._app.service('test', 'foo')

    def _without_parameters(self):
        return 'without'

    def test_factory(self):
        sut = App()
        factory = sut.service('core', 'factory')
        self.assertIsInstance(factory, Factory)

        # Confirm the default factory can at least use simple specifications.
        instance = factory.new(self._without_parameters)
        self.assertEqual(instance, 'without')

    def test_service_inifite_loop(self):
        sut = App()
        sut.add_extension(self.TestExtension)
        with self.assertRaises(FactoryError):
            sut.service('test', 'foo')

    def testServiceWithNonExistentExtension(self):
        sut = App()
        with self.assertRaises(ExtensionNotFound):
            sut.service('i_do_not_exist', 'factory')

    def testServiceWithNonExistentService(self):
        sut = App()
        with self.assertRaises(ServiceNotFound):
            sut.service('core', 'i_do_not_exist')
