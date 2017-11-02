from contracts import contract


@contract
def qualname(cls) -> str:
    separator = ':' if '.' in cls.__qualname__ else '.'
    return cls.__module__ + separator + cls.__qualname__


@contract
def indent(string: str, indentation='   '):
    """
    Indents each line of a multi-line string.
    :param string:
    :param indentation:
    :return:
    """
    return "\n".join(
        map(lambda line: '%s%s' % (indentation, line), string.split("\n")))
