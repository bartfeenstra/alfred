import abc
import traceback
from typing import Iterable, Optional, Callable

from contracts import contract, ContractsMeta, with_metaclass

from alfred import indent, qualname


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


class ExtensionNotFound(LookupError):
    pass


class ServiceNotFound(LookupError):
    pass


class FactoryError(BaseException):
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
                (spec.__name__, indent(traceback.format_exc())))
        pass


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
        pass


class MultipleFactories(Factory):
    def __init__(self):
        self._factories = []
        self._loop = False

    @contract
    def add_factory(self, factory: Factory):
        self._factories.append(factory)

    def new(self, spec):
        if not self._factories:
            raise FactoryError(
                'No factories available. Add them through .add_factory().')

        requirements = []
        for factory in self._factories:
            try:
                return factory.new(spec)
            except FactoryError:
                requirements.append(
                    indent(traceback.format_exc()))
        message = [
            'Could not use specification "%s". One of the following requirements must be met:' % str(
                # noqa: E501
                spec)]

        requirements = set(requirements)
        for requirement in requirements:
            message.append("\n".join(
                map(lambda line: '    %s' % line, requirement.split("\n"))))
            message.append('OR')
        message = message[:-1]

        raise FactoryError("\n".join(message))


class ServiceDefinition:
    def __init__(self, name: str, factory,
                 tags: Optional[Iterable[str]] = None,
                 weight: int = 0):
        self._name = name
        self._factory = factory
        self._tags = tags if tags is not None else []
        self._weight = weight

    def __str__(self):
        return 'Service "%s"' % self.name

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
        """
        Decorates a method and marks it as a service definition.
        :return:
        """

        def __init__(self, name: Optional[str] = None,
                     tags: Optional[Iterable[str]] = None):
            self._name = name
            self._tags = tags if tags is not None else []
            self._factory = None

        def __call__(self, factory):
            self._factory = factory
            return self

        def get_definition(self, instance):
            def factory(*args, **kwargs):
                return self._factory(instance, *args, **kwargs)

            name = self._name if self._name is not None else self._factory.__name__.strip(
                '_')
            return ServiceDefinition(name, factory, self._tags)

    def __init__(self, app: 'App'):
        self._app = app
        self._service_definitions = []

    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        pass

    @classmethod
    def from_app(cls, app):
        """
        Constructs a new instance based on an application.
        :param app:
        :return:
        """
        return cls(app)

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
        callable_factory_definition = ServiceDefinition('factory.callable',
                                                        lambda: CallableFactory(),
                                                        ('factory',))
        self._add_bootstrap_service(callable_factory_definition)
        class_factory_definition = ServiceDefinition('factory.class',
                                                     lambda: ClassFactory(),
                                                     ('factory',))
        self._add_bootstrap_service(class_factory_definition)
        multiple_factory_definition = ServiceDefinition('factory.multiple',
                                                        self._multiple_factory_factory)
        self._add_bootstrap_service(multiple_factory_definition)
        factory_definition = ServiceDefinition('factory',
                                               self._factory_factory)
        self._add_bootstrap_service(factory_definition)

    @contract
    def _add_bootstrap_service(self, definition: ServiceDefinition):
        self._service_definitions.setdefault('core', {})
        self._services.setdefault('core', {})
        self._service_definitions['core'][
            definition.name] = definition
        self._services['core'][definition.name] = LazyValue(
            definition.factory)

    @property
    def factory(self) -> Factory:
        return self.service('core', 'factory')

    @contract
    def _multiple_factory_factory(self) -> Factory:
        factory = MultipleFactories()
        for tagged_factory in self.services(tag='factory'):
            factory.add_factory(tagged_factory)
        return factory

    @contract
    def _factory_factory(self) -> Factory:
        # This is just an alias.
        return self.service('core', 'factory.multiple')

    @contract
    def _add_service(self, extension_name: str,
                     service_definition: ServiceDefinition):
        service = self.factory.defer(service_definition.factory)
        self._service_definitions.setdefault(extension_name, {})
        self._service_definitions[extension_name][
            service_definition.name] = service_definition
        self._services.setdefault(extension_name, {})
        self._services[extension_name][
            service_definition.name] = service

        # @todo This is a workaround to make the factory work. It should
        #  eventually be replaced by an event dispatcher and events for adding
        #  (and removing) extensions.
        if 'factory' in service_definition.tags:
            self.service('core', 'factory.multiple').add_factory(
                self.service(extension_name, service_definition.name))

    @property
    @contract
    def extensions(self) -> Iterable:
        return list(self._extensions.values())

    def add_extension(self, extension_class: type):
        assert issubclass(extension_class, Extension)

        for dependency_extension_class in extension_class.dependencies():
            self.add_extension(dependency_extension_class)

        extension = extension_class.from_app(self)

        self._extensions[extension.name] = extension

        self._services.setdefault(extension.name, {})
        for service_definition in extension.service_definitions:
            self._add_service(extension.name(), service_definition)

    @contract
    def service(self, extension_name: str, service_name: str):
        if (extension_name, service_name) in self._service_stack:
            self._service_stack.append((extension_name, service_name))
            trace = []
            entry = 1
            for frame_extension_name, frame_service_name in self._service_stack:
                trace.append('%d ) Service %s for extension %s.' % (
                    entry, frame_service_name, frame_extension_name))
                entry += 1
            raise RecursionError(
                'Infinite loop when requesting service %s for extension %s twice. Stack trace, with the original service request first:\n%s' % (
                    service_name, extension_name,
                    indent('\n'.join(trace))))

        self._service_stack.append((extension_name, service_name))
        try:
            extension_services = self._services[extension_name]
            try:
                return extension_services[service_name].value
            except FactoryError:
                raise FactoryError(
                    'Could not request service %s for extension %s.' % (
                        service_name, extension_name))
            except KeyError:
                raise ServiceNotFound(
                    'Could not find service "%s" for extension "%s". Did you mean one of the following: %s?' %
                    (service_name, extension_name,
                     ', '.join(extension_services.keys())))
        except KeyError:
            raise ExtensionNotFound(
                'Could not find extension "%s" Did you mean one of the following: %s?' %
                (extension_name,
                 ', '.join(self._service_definitions.keys())))
        finally:
            self._service_stack.pop()

    def services(self, tag: Optional[str] = None) -> Iterable:
        zipped_definitions = []
        for extension_name, definitions in self._service_definitions.items():
            for definition in definitions.values():
                zipped_definitions.append((extension_name, definition))

        if tag is not None:
            zipped_definitions = filter(
                lambda zipped_definition: tag in zipped_definition[1].tags,
                zipped_definitions)

        zipped_definitions = sorted(zipped_definitions,
                                    key=lambda definition: definition[
                                        1].weight)

        services = []
        for zipped_definition in zipped_definitions:
            services.append(
                self.service(zipped_definition[0], zipped_definition[1].name))
        return services
