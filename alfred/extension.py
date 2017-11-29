import abc

from alfred import qualname
from alfred.app import Extension, App, FactoryError, Factory


class AppAwareFactory:
    """
    Allows classes to instantiate themselves using the application.
    """

    @classmethod
    @abc.abstractmethod
    def from_app(cls, app: App):
        """
        Returns a new instance using the application.
        :param app: App
        :return: cls
        """
        pass


class AppAwareCallableFactory(Factory):
    def __init__(self, app: App):
        super().__init__()
        self._app = app

    def new(self, spec):
        if not callable(spec):
            raise FactoryError(
                'Specification must be a callable, but is a %s.' % type(spec))
        try:
            return spec(self._app)
        except Exception as e:
            raise FactoryError(
                'Fix the following error that occurs when %s() is called: %s' %
                (spec, e))


class AppAwareClassFactory(Factory):
    def __init__(self, app: App):
        super().__init__()
        self._app = app

    def new(self, spec):
        if not isinstance(spec, type):
            raise FactoryError(
                'Specification must be a class, but is a %s.' % type(spec))
        try:
            instance = spec.from_app(self._app)
            assert isinstance(instance, spec)
            return instance
        except Exception as e:
            raise FactoryError(
                'Fix the following error that occurs in %s.from_app(): %s' %
                (qualname(spec), e))


class CoreExtension(Extension):
    @staticmethod
    def name():
        return 'core'

    @Extension.service(tags=('factory',))
    def _callable_factory(self):
        return AppAwareCallableFactory(self._app)

    @Extension.service(tags=('factory',), weight=-999)
    def _class_factory(self):
        return AppAwareClassFactory(self._app)
