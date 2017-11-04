from unittest import TestCase
from unittest.mock import patch

from contracts import contract

from alfred import qualname
from alfred.app import App, FactoryError
from alfred.extension import AppAwareCallableFactory, AppAwareClassFactory, \
    CoreExtension, AppAwareFactory


class AppAwareCallableFactoryTest(TestCase):
    def _app_unaware(self):
        pass

    @contract
    def _app_aware(self, app: App):
        return 'app_aware'

    @patch(qualname(App), spec=App)
    def test_success(self, app: App):
        sut = AppAwareCallableFactory(app)
        instance = sut.new(self._app_aware)
        self.assertEquals(instance, 'app_aware')

    @patch(qualname(App), spec=App)
    def test_error(self, app: App):
        sut = AppAwareCallableFactory(app)
        with self.assertRaises(FactoryError):
            sut.new(self._app_unaware)


class AppAwareClassFactoryTest(TestCase):
    class AppUnaware:
        pass

    class AppAware(AppAwareFactory):
        @contract
        def __init__(self, app: App):
            pass

        @classmethod
        def from_app(cls, app):
            return cls(app)

    @patch(qualname(App), spec=App)
    def test_success(self, app: App):
        sut = AppAwareClassFactory(app)
        instance = sut.new(self.AppAware)
        self.assertIsInstance(instance, self.AppAware)

    @patch(qualname(App), spec=App)
    def test_error(self, app: App):
        sut = AppAwareClassFactory(app)
        with self.assertRaises(FactoryError):
            sut.new(self.AppUnaware)


class CoreExtensionTest(TestCase):
    class AppAware:
        @contract
        def __init__(self, app: App):
            pass

    @contract
    def _app_aware(self, app: App):
        return 'app_aware'

    def test_factories(self):
        app = App()
        app.add_extension(CoreExtension)
        instance = app.factory.new(self._app_aware)
        self.assertEquals(instance, 'app_aware')
        instance = app.factory.new(self.AppAware)
        self.assertIsInstance(instance, self.AppAware)
