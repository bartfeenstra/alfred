from copy import copy
from unittest import TestCase

from alfred_json.rewriter import IdentifiableDataTypeAggregator, Rewriter, \
    NestedRewriter
from alfred_json.type import IdentifiableDataType
from alfred_rest.tests import RestTestCase


class IdentifiableDataTypeAggregatorTest(TestCase):
    def testRewriteWithoutDataTypes(self):
        sut = IdentifiableDataTypeAggregator()
        original_schema = {
            'id': 'https://example.com/schema',
            'foo': {
                '$ref': 'https://example.com/schema#',
            },
            'bar': {
                'oneOf': [
                    {
                        '$schema': 'https://example.com/schema#'
                    },
                ],
            },
        }
        rewritten_schema = copy(original_schema)
        sut.rewrite(original_schema)
        self.assertEqual(original_schema, rewritten_schema)

    def testRewriteSimpleDataType(self):
        sut = IdentifiableDataTypeAggregator()
        original_schema = {
            'id': 'https://example.com/schema',
            'foo': IdentifiableDataType({
                'type': 'float',
            }, 'Foo'),
        }
        expected_schema = {
            'id': 'https://example.com/schema',
            'foo': {
                '$ref': '#/definitions/data/Foo',
            },
            'definitions': {
                'data': {
                    'Foo': {
                        'type': 'float',
                    },
                },
            },
        }
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema, expected_schema)

    def testRewriteNestedDataTypes(self):
        sut = IdentifiableDataTypeAggregator()
        original_schema = {
            'id': 'https://example.com/schema',
            'foo': IdentifiableDataType({
                'type': 'float',
            }, 'Foo'),
            'bar': {
                'type': 'object',
                'properties': {
                    'baz': IdentifiableDataType({
                        'type': 'string',
                    }, 'Baz'),
                },
            },
        }
        expected_schema = {
            'id': 'https://example.com/schema',
            'foo': {
                '$ref': '#/definitions/data/Foo',
            },
            'bar': {
                'type': 'object',
                'properties': {
                    'baz': {
                        '$ref': '#/definitions/data/Baz',
                    },
                },
            },
            'definitions': {
                'data': {
                    'Foo': {
                        'type': 'float',
                    },
                    'Baz': {
                        'type': 'string',
                    },
                },
            },
        }
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema, expected_schema)

    def testRewriteDuplicateDataTypes(self):
        sut = IdentifiableDataTypeAggregator()
        data_type = IdentifiableDataType({
            'type': 'float',
        }, 'Foo')
        original_schema = {
            'id': 'https://example.com/schema',
            'foo': data_type,
            'foo2': data_type,
        }
        expected_schema = {
            'id': 'https://example.com/schema',
            'foo': {
                '$ref': '#/definitions/data/Foo',
            },
            'foo2': {
                '$ref': '#/definitions/data/Foo',
            },
            'definitions': {
                'data': {
                    'Foo': {
                        'type': 'float',
                    },
                },
            },
        }
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema, expected_schema)

    def testRewriteExistingDefinition(self):
        sut = IdentifiableDataTypeAggregator()
        data_type_foo = IdentifiableDataType({
            'type': 'float',
        }, 'Foo')
        data_type_bar = IdentifiableDataType({
            'type': 'array',
            'items': data_type_foo,
        }, 'Bar')
        data_type_baz = IdentifiableDataType({
            'type': 'array',
            'items': data_type_bar,
        }, 'Baz')
        original_schema = {
            'id': 'https://example.com/schema',
            'definitions': {
                'data': {
                    'Bar': data_type_bar,
                    'Baz': data_type_baz,
                },
            },
        }
        expected_schema = {
            'id': 'https://example.com/schema',
            'definitions': {
                'data': {
                    'Foo': {
                        'type': 'float',
                    },
                    'Bar': {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/data/Foo',
                        },
                    },
                    'Baz': {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/data/Bar',
                        },
                    },
                },
            },
        }
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema, expected_schema)


class ExternalReferenceProxyTest(RestTestCase):
    ORIGINAL_EXTERNAL_POINTER = 'http://json-schema.org/draft-04/schema#'
    REWRITTEN_EXTERNAL_POINTER = 'http://127.0.0.1:5000/about/json/external-schema/aHR0cDovL2pzb24tc2NoZW1hLm9yZy9kcmFmdC0wNC9zY2hlbWE%3D'
    ALFRED_POINTER = 'http://127.0.0.1:5000/about/json/schema#definitions/data/Foo'
    INTERNAL_POINTER = '#/definitions/data/Bar'

    def testRewritePointerWithNonStringShouldPassThrough(self):
        pointer = {}
        sut = self._app.service('rest', 'external_reference_proxy')
        self.assertEqual(sut.rewrite_pointer(pointer), pointer)

    def testRewritePointerWithAlfredPointerShouldPassThrough(self):
        sut = self._app.service('rest', 'external_reference_proxy')
        self.assertEqual(sut.rewrite_pointer(
            self.ALFRED_POINTER), self.ALFRED_POINTER)

    def testRewritePointerWithInternalPointerShouldPassThrough(self):
        sut = self._app.service('rest', 'external_reference_proxy')
        self.assertEqual(sut.rewrite_pointer(
            self.INTERNAL_POINTER), self.INTERNAL_POINTER)

    def testRewritePointerWithExternalPointerShouldBeRewritten(self):
        sut = self._app.service('rest', 'external_reference_proxy')
        self.assertEqual(sut.rewrite_pointer(
            self.ORIGINAL_EXTERNAL_POINTER), self.REWRITTEN_EXTERNAL_POINTER)

    def testRewrite(self):
        original_schema = {
            'id': self.ORIGINAL_EXTERNAL_POINTER,
            'foo': {
                '$ref': self.ORIGINAL_EXTERNAL_POINTER,
            },
            'bar': {
                '$ref': self.ALFRED_POINTER,
            },
            'baz': {
                '$ref': self.INTERNAL_POINTER,
            },
            'qux': {
                'oneOf': [
                    {
                        '$schema': self.ORIGINAL_EXTERNAL_POINTER
                    },
                ],
            },
        }
        expected_schema = {
            'id': self.REWRITTEN_EXTERNAL_POINTER,
            'foo': {
                '$ref': self.REWRITTEN_EXTERNAL_POINTER,
            },
            'bar': {
                '$ref': self.ALFRED_POINTER,
            },
            'baz': {
                '$ref': self.INTERNAL_POINTER,
            },
            'qux': {
                'oneOf': [
                    {
                        '$schema': self.REWRITTEN_EXTERNAL_POINTER
                    },
                ],
            },
        }
        sut = self._app.service('rest', 'external_reference_proxy')
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema, expected_schema)


class NestedRewriterTest(RestTestCase):
    class DogRewriter(Rewriter):
        def rewrite(self, schema):
            schema['required'].append('woof')
            return schema

    class CatRewriter(Rewriter):
        def rewrite(self, schema):
            schema['required'].append('meow')
            return schema

    def testRewrite(self):
        sut = NestedRewriter()
        sut.add_rewriter(self.DogRewriter())
        sut.add_rewriter(self.CatRewriter())
        original_schema = {
            'type': 'object',
            'required': [],
        }
        expected_schema = {
            'type': 'object',
            'required': ['woof', 'meow'],
        }
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema, expected_schema)
