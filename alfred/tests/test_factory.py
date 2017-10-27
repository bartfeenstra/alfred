from unittest import TestCase
from unittest.mock import patch

from contracts import contract

from alfred import qualname
from alfred.app import App, AppAwareFactory
from alfred.factory import ClassFactory, ClassInstantiationError
from alfred.tests import data_provider


class AppUnawareWithoutConstructorParameters:
    pass


class AppAwareWithoutConstructorParameters(AppAwareFactory):
    @classmethod
    def new_from_app(cls, app):
        return cls()


class AppAwareWithConstructorParameters(AppAwareFactory):
    @contract
    def __init__(self, app: App):
        pass

    @classmethod
    def new_from_app(cls, app):
        return cls(app)


class AppUnawareWithConstructorParameters:
    def __init__(self, app: App):
        pass


def success_classes():
    return {
        AppUnawareWithoutConstructorParameters.__name__: (
            AppUnawareWithoutConstructorParameters,
        ),
        AppAwareWithoutConstructorParameters.__name__: (
            AppAwareWithoutConstructorParameters,
        ),
        AppAwareWithConstructorParameters.__name__: (
            AppAwareWithConstructorParameters,
        ),
    }


def error_classes():
    return {
        AppUnawareWithConstructorParameters.__name__: (
            AppUnawareWithConstructorParameters,
        ),
    }


class ClassFactoryTest(TestCase):
    @patch(qualname(App), spec=App)
    @data_provider(success_classes)
    @contract
    def test_success(self, app: App, cls: type):
        sut = ClassFactory(app)
        sut.new(cls)

    @patch(qualname(App), spec=App)
    @data_provider(error_classes)
    @contract
    def test_error(self, app: App, cls: type):
        sut = ClassFactory(app)
        with self.assertRaises(ClassInstantiationError):
            sut.new(cls)
