import abc
import traceback
from typing import Iterable, Optional, Callable

from contracts import contract, ContractsMeta, with_metaclass

from alfred import indent, qualname, format_iter


class LazyValue:
    def __init__(self, factory: Callable):
        """

        :param factory: A callable that has no required parameters.
        """
        self._factory = factory
        self._produced = False
        self._value = None

    @property
    def value(self):
        return self._produce()

    def __get__(self, instance, owner):
        return self._produce()

    def _produce(self):
        if not self._produced:
            self._value = self._factory()
            self._produced = True
        return self._value


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


class FactoryError(RuntimeError):
    pass


class Factory:
    @contract
    def defer(self, spec) -> LazyValue:
        def lazy_factory():
            return self.new(spec)

        return LazyValue(lazy_factory)

    def new(self, spec):
        pass


class CallableFactory(Factory):
    def new(self, spec):
        if not callable(spec):
            raise FactoryError(
                'Specification must be a callable, but is a %s.' % type(spec))
        try:
            return spec()
        except Exception:
            raise FactoryError(
                'Fix the following error that occurs when %s() is called:\n%s' %
                (spec, indent(traceback.format_exc())))


class ClassFactory(Factory):
    def new(self, spec):
        if not isinstance(spec, type):
            raise FactoryError(
                'Specification must be a class, but is a %s.' % type(spec))
        try:
            return spec()
        except Exception as e:
            raise FactoryError(
                "Fix the following error that occurs in %s.__init__():\n%s" %
                (qualname(spec), indent(traceback.format_exc())))


class MultipleFactories(Factory):
    def __init__(self):
        self._factories = []
        self._loop = False

    @contract
    def set_factories(self, factories: Iterable):
        self._factories = factories

    def new(self, spec):
        if not self._factories:
            raise FactoryError(
                'No factories available. Add them through .add_factory().')

        requirements = []
        for factory in self._factories:
            try:
                instance = factory.new(spec)
                return instance
            except FactoryError:
                requirements.append(
                    indent(traceback.format_exc()))
        message = [
            'Could not use specification "%s". One of the following requirements must be met:' % str(
                spec)]

        requirements = set(requirements)
        for requirement in requirements:
            message.append("\n".join(
                map(lambda line: '    %s' % line, requirement.split("\n"))))
            message.append('OR')
        message = message[:-1]

        raise FactoryError("\n".join(message))


class ServiceDefinition:
    def __init__(self, extension_name: str, name: str, factory,
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
            return ServiceDefinition(instance.name(), name, self.NamedServiceFactory(self._factory, instance), self._tags, weight=self._weight)

    def __init__(self, app: 'App'):
        self._app = app
        self._service_definitions = []

    @classmethod
    def from_app(cls, app):
        """
        Constructs a new instance based on an application.
        :param app:
        :return:
        """
        return cls(app)

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
    def __init__(self):
        self._extensions = {}
        self._service_definitions = {}
        self._services = {}
        self._service_stack = []
        self._bootstrap()

    def _bootstrap(self):
        """
        Adds required core services.
        Optional core services are added through CoreExtension.
        :return:
        """

        callable_factory_definition = ServiceDefinition('core', 'factory.callable',
                                                        lambda: CallableFactory(),
                                                        ('factory',))
        self._add_bootstrap_service(callable_factory_definition)
        class_factory_definition = ServiceDefinition('core', 'factory.class',
                                                     lambda: ClassFactory(),
                                                     ('factory',))
        self._add_bootstrap_service(class_factory_definition)
        multiple_factory_definition = ServiceDefinition('core', 'factory.multiple',
                                                        self._multiple_factory_factory)
        self._add_bootstrap_service(multiple_factory_definition)
        factory_definition = ServiceDefinition('core', 'factory',
                                               self._factory_factory)
        self._add_bootstrap_service(factory_definition)

    @contract
    def _add_bootstrap_service(self, definition: ServiceDefinition):
        assert 'core' == definition.extension_name
        self._service_definitions.setdefault(definition.extension_name, {})
        self._services.setdefault(definition.extension_name, {})
        self._service_definitions[definition.extension_name][
            definition.name] = definition
        self._services[definition.extension_name][definition.name] = LazyValue(
            definition.factory)

    @property
    def factory(self) -> Factory:
        return self.service('core', 'factory')

    @contract
    def _multiple_factory_factory(self) -> Factory:
        factory = MultipleFactories()
        factory.set_factories(self.services(tag='factory'))
        return factory

    @contract
    def _factory_factory(self) -> Factory:
        # This is just an alias.
        return self.service('core', 'factory.multiple')

    @contract
    def _add_service(self, service_definition: ServiceDefinition):
        service = self.factory.defer(service_definition.factory)
        self._service_definitions.setdefault(
            service_definition.extension_name, {})
        self._service_definitions[service_definition.extension_name][
            service_definition.name] = service_definition
        self._services.setdefault(service_definition.extension_name, {})
        self._services[service_definition.extension_name][
            service_definition.name] = service

    def add_extension(self, extension_class: type):
        assert issubclass(extension_class, Extension)

        for dependency_extension_class in extension_class.dependencies():
            self.add_extension(dependency_extension_class)

        extension = extension_class.from_app(self)

        self._extensions[extension.name()] = extension

        self._services.setdefault(extension.name(), {})
        for service_definition in extension.service_definitions:
            assert service_definition.extension_name == extension.name()
            self._add_service(service_definition)

        # @todo This is a workaround to make the factory work. It should
        #  eventually be replaced by an event dispatcher and events for adding
        #  (and removing) extensions.
        self.service('core', 'factory.multiple').set_factories(
            self.services(tag='factory'))

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

        # Check for infinite loops.
        if service_definition in self._service_stack:
            self._service_stack.append(service_definition)
            raise RecursiveServiceDependency(
                'Infinite loop when requesting service %s for extension %s twice. Stack trace, with the original service request first:\n%s' % (
                    service_name, extension_name,
                    indent(format_iter(self._service_stack))))

        # Retrieve the service.
        self._service_stack.append(service_definition)
        try:
            return self._services[extension_name][service_name].value
        except ExtensionError as e:
            raise e
        except ServiceError as e:
            raise e
        except FactoryError as e:
            raise e
        # Convert non-API exceptions to API-specific exceptions.
        except Exception:
            raise FactoryError(
                'Could not request service %s for extension %s.' % (
                    service_name, extension_name))
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
