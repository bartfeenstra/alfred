from unittest import TestCase

import requests_mock
from requests import HTTPError

from alfred.tests import expand_data, data_provider
from alfred_rest.json import Json, get_schema
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
    pass


class RewriterTest(RestTestCase):
    pass
