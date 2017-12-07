from copy import copy
from unittest import TestCase

import requests_mock
from requests import HTTPError

from alfred.tests import expand_data, data_provider
from alfred_rest.json import Json, get_schema, Validator, \
    InternalReferenceAggregator, DataType, Rewriter, NestedRewriter
from alfred_rest.tests import RestTestCase

SCHEMA = {
    'type': 'object',
    'properties': {
        'fruit_name': {
            'type': 'string',
            'pattern': '^[A-Z]',
        },
        'max_per_day': {
            'type': 'integer',
        },
    },
    'required': ['fruit_name'],
}


def provide_4xx_codes():
    """
    Returns the HTTP 4xx codes.
    See data_provider().
    """
    return expand_data(
        list(range(400, 418)) + list(range(421, 424)) + [426, 428, 429, 431,
                                                         451])


def provide_5xx_codes():
    """
    Returns the HTTP 5xx codes.
    See data_provider().
    """
    return expand_data(list(range(500, 508)) + [510, 511])


class JsonTest(TestCase):
    def testData(self):
        data = {
            'Foo': 'Bar',
        }
        raw = '{"Foo": "Bar"}'
        self.assertEqual(Json.from_data(data).data, data)
        self.assertEqual(Json.from_data(data).raw, raw)

    def testRaw(self):
        data = {
            'Foo': 'Bar',
        }
        raw = '{"Foo": "Bar"}'
        self.assertEqual(Json.from_raw(raw).data, data)
        self.assertEqual(Json.from_raw(raw).raw, raw)


class GetSchemaTest(TestCase):
    @requests_mock.mock()
    def testSuccess(self, m):
        url = 'https://example.com/the_schema_path'
        m.get(url, json=SCHEMA)
        schema = get_schema(url)
        self.assertEqual(schema.data, SCHEMA)

    @requests_mock.mock()
    @data_provider(provide_4xx_codes)
    def testFailureWithUpstreamHttp4xxResponse(self, m, upstream_status_code):
        url = 'https://example.com/the_schema_path'
        m.get(url, status_code=upstream_status_code)
        with self.assertRaises(HTTPError):
            get_schema(url)

    @requests_mock.mock()
    @data_provider(provide_5xx_codes)
    def testFailureWithUpstreamHttp5xxResponse(self, m, upstream_status_code):
        url = 'https://example.com/the_schema_path'
        m.get(url, status_code=upstream_status_code)
        with self.assertRaises(HTTPError):
            get_schema(url)


class ValidatorTest(TestCase):
    def testWithExpectedObjectShouldFailOnNonObject(self):
        validator = Validator()
        with self.assertRaises(ValueError):
            validator.validate(Json.from_data('Foo'))

    def testWithExpectedObjectShouldFailOnMissingSchemaKey(self):
        validator = Validator()
        with self.assertRaises(KeyError):
            validator.validate(Json.from_data({}))

    def testSuccess(self):
        validator = Validator()
        data = Json.from_data({
            'fruit_name': 'Apple',
        })
        validator.validate(data, Json.from_data(SCHEMA))


class InternalReferenceAggregatorTest(TestCase):
    def testRewriteWithoutReferenes(self):
        sut = InternalReferenceAggregator()
        original_schema = Json.from_data({
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
        })
        rewritten_schema = copy(original_schema)
        sut.rewrite(original_schema)
        self.assertEqual(original_schema.data, rewritten_schema.data)

    def testRewriteSimpleReference(self):
        sut = InternalReferenceAggregator()
        original_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': DataType('Foo', Json.from_data({
                'type': 'float',
            })),
        })
        expected_schema = Json.from_data({
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
        })
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema.data, expected_schema.data)

    def testRewriteNestedReferences(self):
        sut = InternalReferenceAggregator()
        original_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': DataType('Foo', Json.from_data({
                'type': 'float',
            })),
            'bar': {
                'type': 'object',
                'properties': {
                    'baz': DataType('Baz', Json.from_data({
                        'type': 'string',
                    })),
                },
            },
        })
        expected_schema = Json.from_data({
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
        })
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema.data, expected_schema.data)

    def testRewriteDuplicateReferences(self):
        sut = InternalReferenceAggregator()
        data_type = DataType('Foo', Json.from_data({
            'type': 'float',
        }))
        original_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': data_type,
            'foo2': data_type,
        })
        expected_schema = Json.from_data({
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
        })
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema.data, expected_schema.data)


class ExternalReferenceProxyTest(RestTestCase):
    ORIGINAL_EXTERNAL_POINTER = 'http://json-schema.org/draft-04/schema#'
    REWRITTEN_EXTERNAL_POINTER = 'http://127.0.0.1:5000/about/json/external-schema/aHR0cDovL2pzb24tc2NoZW1hLm9yZy9kcmFmdC0wNC9zY2hlbWE%3D'
    ALFRED_POINTER = 'http://127.0.0.1:5000/about/json/schema#definitions/data/Foo'
    INTERNAL_POINTER = '/#definitions/data/Bar'

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
        original_schema = Json.from_data({
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
        })
        expected_schema = Json.from_data({
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
        })
        sut = self._app.service('rest', 'external_reference_proxy')
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema.data, expected_schema.data)


class NestedRewriterTest(RestTestCase):
    class DogRewriter(Rewriter):
        def rewrite(self, schema: Json):
            schema.data['required'].append('woof')
            return schema

    class CatRewriter(Rewriter):
        def rewrite(self, schema: Json):
            schema.data['required'].append('meow')
            return schema

    def testRewritePointerWithNonStringShouldPassThrough(self):
        sut = NestedRewriter()
        sut.add_rewriter(self.DogRewriter())
        sut.add_rewriter(self.CatRewriter())
        original_schema = Json.from_data({
            'type': 'object',
            'required': [],
        })
        expected_schema = Json.from_data({
            'type': 'object',
            'required': ['woof', 'meow'],
        })
        rewritten_schema = sut.rewrite(original_schema)
        self.assertEqual(rewritten_schema.data, expected_schema.data)
