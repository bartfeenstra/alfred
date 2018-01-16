import abc
from typing import Iterable, Optional, Callable

from contracts import contract, ContractsMeta, with_metaclass

from alfred import indent, format_iter


class ExtensionError(BaseException):
    pass


class ExtensionNotFound(LookupError, ExtensionError):
    pass


class ServiceError(BaseException):
    pass


class ServiceNotFound(LookupError, ServiceError):
    pass


class RecursiveServiceDependency(RecursionError, ServiceError):
    pass


class ServiceDefinition:
    def __init__(self, extension_name: str, name: str, factory: Callable,
                 tags: Optional[Iterable[str]] = None,
                 weight: int = 0):
        self._extension_name = extension_name
        self._name = name
        self._factory = factory
        self._tags = tags if tags is not None else []
        self._weight = weight

    def __str__(self):
        return 'Service "%s" for extension "%s"' % (
            self.name, self.extension_name)

    @property
    def extension_name(self):
        return self._extension_name

    @property
    def name(self):
        return self._name

    @property
    def factory(self):
        return self._factory

    @property
    def tags(self):
        return self._tags

    @property
    def weight(self):
        return self._weight


class Extension(with_metaclass(ContractsMeta)):
    """
    Extensions integrate share their functionality with the rest of the app.

    Shared functionality is achieved through services. These provide key
    functionality, and are instantiated once and re-used throughout the
    application. The .service_definitions property exposes each extension's
    services to the application. The following shortcut is available:
    - Any method decorated with Extension.service() will be exposed
      automatically.
    """

    class service:
        class NamedServiceFactory:
            """
            Wraps a decorated service factory.
            """

            def __init__(self, factory, instance):
                self._factory = factory
                self._instance = instance

            def __call__(self, *args, **kwargs):
                return self._factory(self._instance, *args, **kwargs)

            def __str__(self):
                """
                As __call__ just invokes the wrapped factory, name ourselves
                after it for easy debugging.
                :return:
                """
                return str(self._factory)

        """
        Decorates a method and marks it as a service definition.
        :return:
        """

        def __init__(self, name: Optional[str] = None,
                     tags: Optional[Iterable[str]] = None, weight: int = 0):
            self._name = name
            self._tags = tags if tags is not None else []
            self._factory = None
            self._weight = weight

        def __call__(self, factory, *args, **kwargs):
            self._factory = factory
            return self

        def get_definition(self, instance):
            """

            :param instance: The instance the factory method must be called on.
            :return:
            """
            name = self._name if self._name is not None else self._factory.__name__.strip(
                '_')
            return ServiceDefinition(instance.name(), name,
                                     self.NamedServiceFactory(self._factory,
                                                              instance),
                                     self._tags, weight=self._weight)

    def __init__(self):
        self._service_definitions = []

    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        pass

    @staticmethod
    def dependencies() -> Iterable:
        return []

    @property
    @contract
    def service_definitions(self) -> Iterable:
        for name, attribute in self.__class__.__dict__.items():
            if isinstance(attribute, self.service):
                yield attribute.get_definition(self)


class App:
    """
    Provides Alfred's core application.

    This class allows at most one instance of itself to be active. To active an
    instance, simply call start() and stop(), or use a context:
    >>> app = App()
    >>> # Implicitly call the (de)activation methods.
    >>> app.start()
    >>> # Make the app do something.
    >>> app.stop()
    >>> # Or use a context for this to be done automatically:
    >>> with app:
    >>>     # Make the app do something.
    """

    # The currently running App, or None if no App is running.
    current = None

    def __init__(self):
        self._extensions = {}
        self._service_definitions = {}
        self._services = {}
        self._service_stack = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        if self.__class__.current is not None:
            raise RuntimeError(
                'Another instance of Alfred is already running.')
        self.__class__.current = self

    def stop(self):
        if self.__class__.current is None:
            return
        if self.__class__.current is not self:
            raise RuntimeError(
                'Another instance of Alfred is already running, and it cannot be stopped through this instance.')
        self.__class__.current = None

    @contract
    def _add_service(self, service_definition: ServiceDefinition):
        self._service_definitions.setdefault(
            service_definition.extension_name, {})
        self._service_definitions[service_definition.extension_name][
            service_definition.name] = service_definition

    def add_extension(self, extension_class: type):
        assert issubclass(extension_class, Extension)

        for dependency_extension_class in extension_class.dependencies():
            self.add_extension(dependency_extension_class)

        extension = extension_class()

        self._extensions[extension.name()] = extension

        self._services.setdefault(extension.name(), {})
        for service_definition in extension.service_definitions:
            assert service_definition.extension_name == extension.name()
            self._add_service(service_definition)

    @contract
    def service(self, extension_name: str, service_name: str):
        # Get the extension.
        try:
            extension_service_definitions = self._service_definitions[
                extension_name]
        except KeyError:
            raise ExtensionNotFound(
                'Could not find extension "%s" Did you mean one of the following: %s?' %
                (extension_name,
                 ', '.join(self._service_definitions.keys())))

        # Get the extension's service definition.
        try:
            service_definition = extension_service_definitions[service_name]
        except KeyError:
            raise ServiceNotFound(
                'Could not find service "%s" for extension "%s". Did you mean one of the following: %s?' %
                (service_name, extension_name,
                 ', '.join(extension_service_definitions.keys())))

        # Return the service if we instantiated it before.
        if extension_name in self._services and service_name in self._services[extension_name]:
            return self._services[extension_name][service_name]

        # Check for infinite loops.
        if service_definition in self._service_stack:
            # Add the definition to the stack, so it can be inspected.
            self._service_stack.append(service_definition)
            raise RecursiveServiceDependency(
                'Infinite loop when requesting service "%s" for extension "%s" twice. Stack trace, with the original service request first:\n%s' % (
                    service_name, extension_name,
                    indent(format_iter(self._service_stack))))

        # Instantiate and return the service.
        self._service_stack.append(service_definition)
        try:
            service = service_definition.factory()
            self._services[extension_name][service_name] = service
            return service
        finally:
            self._service_stack.pop()

    def services(self, tag: Optional[str] = None) -> Iterable:
        definitions = []
        for extension_name, extension_definitions in self._service_definitions.items():
            for extension_definition in extension_definitions.values():
                definitions.append(extension_definition)

        if tag is not None:
            definitions = filter(
                lambda definition: tag in definition.tags, definitions)

        definitions = sorted(
            definitions, key=lambda definition: definition.weight)

        services = []
        for definition in definitions:
            services.append(self.service(
                definition.extension_name, definition.name))
        return services
