from contracts import contract


@contract
def qualname(cls) -> str:
    return '%s.%s' % (cls.__module__,  cls.__qualname__)


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
