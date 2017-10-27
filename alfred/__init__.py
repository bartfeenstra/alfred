from contracts import contract


@contract
def qualname(cls) -> str:
    separator = ':' if '.' in cls.__qualname__ else '.'
    return cls.__module__ + separator + cls.__qualname__
