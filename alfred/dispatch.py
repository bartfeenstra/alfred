import itertools
from copy import copy
from functools import update_wrapper, partial, reduce
from typing import Callable

from contracts import contract


class HandlerDefinition:
    @contract
    def __init__(self, handler: Callable, factory: bool = False):
        self._handler = handler
        self._factory = factory

    @property
    @contract
    def handler(self) -> Callable:
        return self._handler

    @property
    @contract
    def factory(self) -> bool:
        return self._factory


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
        handlers = self._handler_definitions

        # Keep those handlers that are on the same instance or class.
        if self._bound_cls:
            handlers = filter(
                lambda x: hasattr(self._bound_cls, x.handler.__name__) and (
                    x.handler == getattr(self._bound_cls,
                                         x.handler.__name__)), handlers)

        # Prepare the handlers.
        handlers = map(self._get_handler, handlers)

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
            raise RuntimeError('No factory exists for this dispatcher.')
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
