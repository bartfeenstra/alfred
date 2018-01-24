from typing import Iterable

from contracts import contract


@contract
def qualname(cls) -> str:
    return '%s.%s' % (cls.__module__, cls.__qualname__)


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


@contract
def format_iter(items: Iterable):
    entry = 1
    formatted = []
    for item in items:
        formatted.append('%d ) %s' % (entry, item))
        entry += 1
    return '\n'.join(formatted)
