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
        self._handlers = [dispatched]
        self._reducer = reducer

    def __get__(self, obj, objtype):
        arg = obj if obj else objtype
        return partial(self.__call__, arg)

    def __call__(self, *args, **kwargs):
        if self._reducer:
            results = map(lambda h: h(*args, **kwargs), self._handlers)
            return reduce(self._reducer, results)
        else:
            for handler in self._handlers:
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
