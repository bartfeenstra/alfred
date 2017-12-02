from unittest import TestCase
from unittest.mock import Mock

import requests_mock
from requests import HTTPError

from alfred.tests import expand_data, data_provider
from alfred_http.endpoints import EndpointUrlBuilder
from alfred_rest.json import Json, get_schema, Validator, Rewriter
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
    return expand_data(list(range(400, 418)) + list(range(421, 424)) + [426, 428, 429, 431, 451])


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


class GetSchemaTest(RestTestCase):
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


class ValidatorTest(RestTestCase):
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


class RewriterTest(RestTestCase):
    ORIGINAL_POINTER = 'http://json-schema.org/draft-04/schema#'
    REWRITTEN_POINTER = 'http://127.0.0.1:5000/about/json/external-schema/aHR0cDovL2pzb24tc2NoZW1hLm9yZy9kcmFmdC0wNC9zY2hlbWE%3D'
    INTERNAL_POINTER = 'http://127.0.0.1:5000/foo/bar/BAZ'

    def testRewritePointerWithNonStringShouldPassThrough(self):
        pointer = {}
        sut = self._app.service('rest', 'json_reference_rewriter')
        self.assertEqual(sut.rewrite_pointer(pointer), pointer)

    def testRewritePointerWithInternalPointerShouldPassThrough(self):
        sut = self._app.service('rest', 'json_reference_rewriter')
        self.assertEqual(sut.rewrite_pointer(self.INTERNAL_POINTER), self.INTERNAL_POINTER)

    def testRewritePointerWithExternalPointerShouldBeRewritten(self):
        sut = self._app.service('rest', 'json_reference_rewriter')
        self.assertEqual(sut.rewrite_pointer(self.ORIGINAL_POINTER), self.REWRITTEN_POINTER)

    def testRewrite(self):
        original_schema = Json.from_data({
            'id': self.ORIGINAL_POINTER,
            'foo': {
                '$ref': self.ORIGINAL_POINTER,
            },
            'bar': {
                '$ref': self.INTERNAL_POINTER,
            },
            'baz': {
                'oneOf': [
                    {
                        '$schema': self.ORIGINAL_POINTER
                    },
                ],
            },
        })
        rewritten_schema = Json.from_data({
            'id': self.REWRITTEN_POINTER,
            'foo': {
                '$ref': self.REWRITTEN_POINTER,
            },
            'bar': {
                '$ref': self.INTERNAL_POINTER,
            },
            'baz': {
                'oneOf': [
                    {
                        '$schema': self.REWRITTEN_POINTER
                    },
                ],
            },
        })
        sut = self._app.service('rest', 'json_reference_rewriter')
        sut.rewrite(original_schema)
        self.assertEqual(original_schema.data, rewritten_schema.data)

