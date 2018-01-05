from functools import update_wrapper, partial, reduce
from typing import Callable

from contracts import contract


class Dispatcher:
    """
    Dispatches a callable's execution to registered handler callables.
    """
    @contract
    def __init__(self, dispatched: Callable, reducer=None):
        update_wrapper(self, dispatched)
        self._handler_self = None
        self._handler_cls = None
        self._handlers = [dispatched]
        self._reducer = reducer

    def __get__(self, obj, objtype):
        self._handler_self = obj
        self._handler_cls = objtype
        return self

    def __call__(self, *args, **kwargs):
        handlers = self._handlers

        # Keep those handlers that are on the same instance or class.
        if self._handler_cls:
            handlers = filter(lambda x: hasattr(self._handler_cls, x.__name__) and (x == getattr(
                self._handler_cls, x.__name__) or isinstance(getattr(self._handler_cls, x.__name__), Dispatcher)), handlers)

            # Apply the instance or class.
            arg = self._handler_self if self._handler_self else self._handler_cls
            handlers = map(lambda x: partial(x, arg), handlers)

        # Invoke all handlers and reduce the results.
        if self._reducer:
            results = map(lambda h: h(*args, **kwargs), handlers)
            return reduce(self._reducer, results)
        # Invoke all handlers and ignore the results.
        else:
            for handler in handlers:
                handler(*args, **kwargs)
            return None

    def register(self):
        @contract
        def decorator(handler: Callable):
            self._handlers.append(handler)
            return handler

        return decorator


def dispatch(*args, **kwargs):
    """
    Creates a decorator to dispatch a callable's execution to other callables.

    This decorator MUST be the outermost decorator on any callable.
    :return:
    """
    return lambda x: Dispatcher(x, *args, **kwargs)
