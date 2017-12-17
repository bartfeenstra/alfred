from copy import copy
from unittest import TestCase
from unittest.mock import MagicMock

from jsonschema import ValidationError

from alfred_http.endpoints import EndpointUrlBuilder
from alfred_rest.json import Json, Validator, \
    IdentifiableDataTypeAggregator, Rewriter, NestedRewriter, \
    IdentifiableDataType, SchemaRepository, SchemaNotFound
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


class ValidatorTest(TestCase):
    class PassThroughRewriter(Rewriter):
        def rewrite(self, schema):
            return schema

    def testValidate(self):
        validator = Validator(self.PassThroughRewriter())
        data = Json.from_data({
            'fruit_name': 'Apple',
        })
        validator.validate(data, Json.from_data(SCHEMA))

    def testValidateWithFailure(self):
        validator = Validator(self.PassThroughRewriter())
        data = Json.from_data({})
        with self.assertRaises(ValidationError):
            validator.validate(data, Json.from_data(SCHEMA))


class IdentifiableDataTypeAggregatorTest(TestCase):
    def testRewriteWithoutDataTypes(self):
        urls = MagicMock(EndpointUrlBuilder)
        urls.build = MagicMock(
            return_value='http://127.0.0.1/about/json/schema')
        sut = IdentifiableDataTypeAggregator(urls)
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
        urls.build.assert_called_once_with('schema')

    def testRewriteSimpleDataType(self):
        urls = MagicMock(EndpointUrlBuilder)
        urls.build = MagicMock(
            return_value='http://127.0.0.1/about/json/schema')
        sut = IdentifiableDataTypeAggregator(urls)
        original_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': IdentifiableDataType(Json.from_data({
                'type': 'float',
            }), 'Foo'),
        })
        expected_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': {
                '$ref': 'http://127.0.0.1/about/json/schema#/definitions/data/Foo',
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
        urls.build.assert_called_once_with('schema')

    def testRewriteNestedDataTypes(self):
        urls = MagicMock(EndpointUrlBuilder)
        urls.build = MagicMock(
            return_value='http://127.0.0.1/about/json/schema')
        sut = IdentifiableDataTypeAggregator(urls)
        original_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': IdentifiableDataType(Json.from_data({
                'type': 'float',
            }), 'Foo'),
            'bar': {
                'type': 'object',
                'properties': {
                    'baz': IdentifiableDataType(Json.from_data({
                        'type': 'string',
                    }), 'Baz'),
                },
            },
        })
        expected_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': {
                '$ref': 'http://127.0.0.1/about/json/schema#/definitions/data/Foo',
            },
            'bar': {
                'type': 'object',
                'properties': {
                    'baz': {
                        '$ref': 'http://127.0.0.1/about/json/schema#/definitions/data/Baz',
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
        urls.build.assert_called_once_with('schema')

    def testRewriteDuplicateDataTypes(self):
        urls = MagicMock(EndpointUrlBuilder)
        urls.build = MagicMock(
            return_value='http://127.0.0.1/about/json/schema')
        sut = IdentifiableDataTypeAggregator(urls)
        data_type = IdentifiableDataType(Json.from_data({
            'type': 'float',
        }), 'Foo')
        original_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': data_type,
            'foo2': data_type,
        })
        expected_schema = Json.from_data({
            'id': 'https://example.com/schema',
            'foo': {
                '$ref': 'http://127.0.0.1/about/json/schema#/definitions/data/Foo',
            },
            'foo2': {
                '$ref': 'http://127.0.0.1/about/json/schema#/definitions/data/Foo',
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
        urls.build.assert_called_once_with('schema')


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


class SchemaRepositoryTest(TestCase):
    def testSchemaShouldFindExactMatch(self):
        schema_id = 'https://example.com/schema#'
        schema = {
            'id': schema_id,
        }
        sut = SchemaRepository()
        sut.add_schema(schema)
        self.assertEquals(sut.get_schema(schema_id), schema)

    def testSchemaShouldFindMatchWithAddedFragment(self):
        schema_id = 'https://example.com/schema#'
        schema = {
            'id': schema_id,
        }
        sut = SchemaRepository()
        sut.add_schema(schema)
        self.assertEquals(sut.get_schema('https://example.com/schema'), schema)

    def testSchemaShouldFindMatchWithRemovedFragment(self):
        schema_id = 'https://example.com/schema'
        schema = {
            'id': schema_id,
        }
        sut = SchemaRepository()
        sut.add_schema(schema)
        self.assertEquals(sut.get_schema('https://example.com/schema#'),
                          schema)

    def testSchemaShouldRaiseErrorForUnknownSchema(self):
        schema_id = 'https://example.com/schema'
        schema = {
            'id': schema_id,
        }
        sut = SchemaRepository()
        sut.add_schema(schema)
        with self.assertRaises(SchemaNotFound):
            sut.get_schema('https://example.com/schema2')

    def testSchemaShouldRaiseErrorForNoSchemas(self):
        schema_id = 'https://example.com/schema#'
        sut = SchemaRepository()
        with self.assertRaises(SchemaNotFound):
            sut.get_schema(schema_id)

    def testGetSchemasWithoutSchemas(self):
        sut = SchemaRepository()
        self.assertEquals(sut.get_schemas(), [])

    def testGetSchemasWithSchemas(self):
        schema_id = 'https://example.com/schema'
        schema = {
            'id': schema_id,
        }
        sut = SchemaRepository()
        sut.add_schema(schema)
        self.assertEquals(sut.get_schemas(), [schema])
