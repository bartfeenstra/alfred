import abc
from typing import Iterable, Dict, Callable

from contracts import contract, ContractsMeta, with_metaclass


class AppAwareFactory:
    @classmethod
    @abc.abstractmethod
    def new_from_app(cls, app: 'App'):
        """
        Returns a new instance using an extension repository.
        :param repository:
        :return: cls
        """
        pass


class Extension(AppAwareFactory,
                with_metaclass(ContractsMeta)):
    def __init__(self, app: 'App'):
        self._app = app

    @staticmethod
    @abc.abstractmethod
    def name():
        pass

    @classmethod
    def new_from_app(cls, app):
        return cls(app)

    @staticmethod
    def dependencies() -> Iterable:
        return []

    @contract
    def get_services(self) -> Dict:
        return {}


class App:
    class Service:
        def __init__(self, factory: Callable):
            self._factory = factory

        def __get__(self, instance, owner):
            service = self._factory()
            setattr(instance, '__get__', service)
            return service

    def __init__(self):
        self._extensions = {}
        self._services = {}

    @property
    @contract
    def extensions(self) -> Iterable:
        return list(self._extensions.values())

    def add_extension(self, extension_class: type):
        assert issubclass(extension_class, Extension)

        for dependency_extension_class in extension_class.dependencies():
            self.add_extension(dependency_extension_class)

        extension = extension_class.new_from_app(self)

        self._extensions[extension.name] = extension

        self._services.setdefault(extension.name, {})
        for name, factory in extension.get_services().items():
            self._services[name] = self.Service(factory)

    @contract
    def service(self, extension_name: str, service_name: str):
        return self._services[extension_name][service_name]
