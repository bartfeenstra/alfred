from unittest import TestCase

from alfred.tests import data_provider
from alfred_json.type import ListType, ScalarType, OutputDataType, \
    InputDataType

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


class ListTypeTest(TestCase):
    class NumberItem(InputDataType, OutputDataType):
        def from_json(self, json_data):
            return json_data * 2

        def to_json(self, data):
            return data / 2

        def get_json_schema(self):
            return {
                'type': 'number',
            }

    def testFromJson(self):
        item_type = self.NumberItem()
        sut = ListType(item_type)
        json_data = [3, 1, 4]
        actual_data = sut.from_json(json_data)
        expected_data = [6, 2, 8]
        self.assertEquals(actual_data, expected_data)

    def testToJson(self):
        item_type = self.NumberItem()
        sut = ListType(item_type)
        data = [6, 2, 8]
        actual_json_data = sut.to_json(data)
        expected_json_data = [3, 1, 4]
        self.assertEquals(actual_json_data, expected_json_data)


def valid_scalar_schemas():
    return {
        'string': ({
                       'type': 'string',
                   },),
        'number': ({
                       'type': 'number',
                   },),
        'boolean': ({
                        'type': 'boolean',
                    },),
        'enum': ({
                     'enum': [1, 'One', True],
                 },),
    }


def invalid_scalar_schemas():
    return {
        'object': ({
                       'type': 'object',
                   },),
        'array': ({
                      'type': 'array',
                  },),
        'enum_with_array': ({
                                'enum': [[1, 'One', True], ],
                            },),
    }


class ScalarTypeTest(TestCase):
    @data_provider(valid_scalar_schemas)
    def testInitWithValidScalarSchemas(self, schema):
        ScalarType(schema)

    @data_provider(invalid_scalar_schemas)
    def testInitWithInvalidScalarSchemas(self, schema):
        with self.assertRaises(ValueError):
            ScalarType(schema)

    def testToJson(self):
        sut = ScalarType({
            'type': 'number',
        })
        data = 3
        self.assertEquals(sut.to_json(data), 3)

    def testFromJson(self):
        sut = ScalarType({
            'type': 'number',
        })
        data = 3
        self.assertEquals(sut.from_json(data), 3)
