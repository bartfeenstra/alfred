from functools import wraps
from unittest import TestCase

from alfred.app import App


def data_provider(data_provider):
    """
    Provides a test method with test data.

    Applying this decorator to a test method causes that method to be run as
    many times as the data provider callable returns dictionary items.
    Failed assertions will include information about which data set failed.

    :param data_provider: A callable that generates the test data as a
      dictionary of tuples containing the test method arguments, keyed by data
      set name.
    :return:
    """
    def decorator(test_method):
        """
        The actual decorator.
        :param test_method: The test method to decorate.
        :return:
        """
        @wraps(test_method)
        def multiplier(self, *test_method_args, **test_method_kwargs):
            """
            The replacement (decorated) test method.
            :param self:
            :param args:
            :return:
            """
            for fixture_name, test_method_fixture_args in data_provider().items():
                try:
                    test_method(self, *test_method_args,
                                *test_method_fixture_args,
                                **test_method_kwargs)
                except AssertionError:
                    raise AssertionError(
                        'Assertion failed with data set "%s"' % str(fixture_name))
                except Exception:
                    raise AssertionError(
                        'Unexpected error with data set "%s"' % str(
                            fixture_name))

        return multiplier

    return decorator


def expand_data(values):
    """
    Expands a data set.
    :param data: An iterable of scalars.
    :return:
    """
    data = {}
    for value in values:
        data[value] = (value,)
    return data


class AppTestCase(TestCase):
    def setUp(self):
        self.addCleanup(self._stopApp)
        self._app = App()
        for extension in self.get_extension_classes():
            self._app.add_extension(extension)
        self._app.start()

    def _stopApp(self):
        self._app.stop()

    def get_extension_classes(self):
        return []
