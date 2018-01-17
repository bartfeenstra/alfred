import itertools
from copy import copy
from functools import update_wrapper, partial, reduce
from typing import Callable

from contracts import contract

from alfred import qualname


class HandlerDefinition:
    @contract
    def __init__(self, handler: Callable, factory: bool = False, weight: int=0):
        self._handler = handler
        self._factory = factory
        self._weight = weight

    @property
    @contract
    def handler(self) -> Callable:
        return self._handler

    @property
    @contract
    def factory(self) -> bool:
        return self._factory

    @property
    @contract
    def weight(self) -> int:
        return self._weight


class Dispatcher:
    """
    Dispatches a callable's execution to registered handler callables.

    Class and static methods are not supported.
    """

    @contract
    def __init__(self, dispatched: Callable, reducer=None, factory=None):
        update_wrapper(self, dispatched)
        self._bound_self = None
        self._bound_cls = None
        self._is_bound = dispatched.__name__ != dispatched.__qualname__
        self._dispatched = dispatched
        self._handler_definitions = []
        self._factory = factory
        self._reducer = reducer

    def __get__(self, obj, objtype):
        if self._is_bound:
            # Return an identical copy of self, but with information about the
            #  bound instance and class. A single, shared copy would suffer
            #  from changing binding information across references.
            clone = copy(self)
            clone._bound_self = obj
            clone._bound_cls = objtype
            return clone
        return self

    def __call__(self, *args, **kwargs):
        handler_definitions = self._handler_definitions

        # Keep those handlers that are on the same instance or class.
        if self._bound_cls:
            handler_definitions = filter(
                lambda x: hasattr(self._bound_cls, x.handler.__name__) and (
                    x.handler == getattr(self._bound_cls,
                                         x.handler.__name__)), handler_definitions)

        handler_definitions = sorted(
            handler_definitions, key=lambda x: x.weight)

        # Load the handlers.
        handlers = map(self._get_handler, handler_definitions)

        # Now all third-party handlers have been processed, prepend the
        #  originally dispatched method, so it's invoked first.
        handlers = itertools.chain([self._get_dispatched()], handlers)

        # Invoke all handlers and reduce the results.
        if self._reducer:
            results = map(lambda h: h(*args, **kwargs), handlers)
            return reduce(self._reducer, results)
        # Invoke all handlers and ignore the results.
        else:
            for handler in handlers:
                handler(*args, **kwargs)
            return None

    @contract
    def _get_handler(self, definition: HandlerDefinition):
        handler = definition.handler

        if definition.factory:
            factory = self._get_factory()
            handler = factory(handler)

        return self._bind(handler)

    def _get_factory(self):
        if not self._factory:
            raise RuntimeError(
                'No factory exists for this dispatcher (%s).' % qualname(self))
        return self._bind(self._factory)

    def _get_dispatched(self):
        return self._bind(self._dispatched)

    @contract
    def _bind(self, callable: Callable):
        """
        Binds a callable, if needed.

        :param callable: Callable
        :return: Callable
        """
        if not self._is_bound:
            return callable

        if not self._bound_self:
            raise RuntimeError('There is no instance to bind the method to.')

        bound = partial(callable, self._bound_self)
        update_wrapper(bound, callable)
        return bound

    def register(self, *args, **kwargs):
        """
        Creates a decorator to dispatch self's execution to the decorated
         method.
        :param args:
        :param kwargs:
        :return: Callable
        """

        def decorator(handler: Callable):
            self._handler_definitions.append(
                HandlerDefinition(handler, *args, **kwargs))
            return handler

        return decorator


def dispatch(*args, **kwargs):
    """
    Creates a decorator to dispatch a callable's execution to other callables.

    This decorator MUST be the outermost decorator on any callable.
    :param args:
    :param kwargs:
    :return: Callable
    """
    return lambda x: Dispatcher(x, *args, **kwargs)


class classproperty:
    @contract
    def __init__(self, fget: Callable, doc=None):
        self._fget = fget
        if doc is None:
            doc = fget.__doc__
        self.__doc__ = doc

    def __get__(self, instance, cls):
        if cls is None:
            cls = type(instance)
        return self._fget(cls)

    def __set__(self, instance, value):
        raise AttributeError('Setting class properties is currently not supported.')

    def __delete__(self, instance):
        raise AttributeError('Deleting class properties is currently not supported.')
