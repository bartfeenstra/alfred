from typing import Iterable
from unittest import TestCase

from alfred_speech.schema.validate import SchemaValueError, Schema


class SchemaTestCase(TestCase):
    class AlwaysInvalidSchema(Schema):
        def validate(self, value):
            return [SchemaValueError()]

    def assertContainsInstance(self, type, instances: Iterable, msg=None):
        for instance in instances:
            if isinstance(instance, type):
                return
        self.fail(self._formatMessage(msg,
                                      'Failed to assert that an instance of %s is contained by %s' % (
                                          str(type), str(instances))))
