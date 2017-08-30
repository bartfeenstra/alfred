from alfred_speech.schema.mutate import ListSchema, DictSchema, \
    NonDeletableValueError, NonSettableValueError
from alfred_speech.schema.tests import SchemaTestCase
from alfred_speech.schema.validate import TypeSchema, SchemaValueError, \
    AnySchema, SchemaKeyError, SchemaTypeError


class ListSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._item_schema = TypeSchema(int)

    def testMutable(self):
        sut = ListSchema(self._item_schema)
        self.assertFalse(sut.mutable)
        sut.mutable = True
        self.assertTrue(sut.mutable)

    def testSetValueWithMutable(self):
        data = []
        value = 3
        sut = ListSchema(self._item_schema)
        sut.mutable = True
        sut.set_value(data, 0, value)
        self.assertEqual(data, [value])

    def testSetValueWithImmutable(self):
        data = []
        value = 3
        sut = ListSchema(self._item_schema)
        sut.mutable = False
        with self.assertRaises(NonSettableValueError):
            sut.set_value(data, 0, value)

    def testSetValueWithInvalidResult(self):
        data = []
        value = '3'
        sut = ListSchema(self._item_schema)
        sut.mutable = True
        with self.assertRaises(SchemaTypeError):
            sut.set_value(data, 0, value)
        self.assertEqual(data, [])

    def testSetValuesWithMutableDecreaseSize(self):
        data = [3, 1, 4]
        value = [3]
        sut = ListSchema(self._item_schema)
        sut.mutable = True
        sut.set_values(data, value)
        self.assertEqual(data, value)

    def testSetValuesWithMutableIncreaseSize(self):
        data = [3]
        value = [3, 1, 4]
        sut = ListSchema(self._item_schema)
        sut.mutable = True
        sut.set_values(data, value)
        self.assertEqual(data, value)

    def testSetValuesWithImmutable(self):
        data = []
        value = [3]
        sut = ListSchema(self._item_schema)
        sut.mutable = False
        with self.assertRaises(NonSettableValueError):
            sut.set_values(data, value)

    def testSetValuesWithInvalidResult(self):
        data = []
        value = ['3']
        sut = ListSchema(self._item_schema)
        sut.mutable = True
        with self.assertRaises(SchemaTypeError):
            sut.set_values(data, value)
        self.assertEqual(data, [])

    def testDeleteValueWithMutable(self):
        data = [3]
        sut = ListSchema(self._item_schema)
        sut.mutable = True
        sut.delete_value(data, 0)
        self.assertEqual(data, [])

    def testDeleteValueWithImmutable(self):
        data = [3]
        sut = ListSchema(self._item_schema)
        sut.mutable = False
        with self.assertRaises(NonDeletableValueError):
            sut.delete_value(data, 0)

    def testDeleteValueWithInvalidResult(self):
        data = [3]
        sut = ListSchema(self._item_schema, min_length=1)
        sut.mutable = True
        sut.assert_valid(data)
        with self.assertRaises(SchemaValueError):
            sut.delete_value(data, 0)
        self.assertEqual(data, [3])

    def testDeleteValuesWithMutable(self):
        data = [3]
        sut = ListSchema(self._item_schema)
        sut.mutable = True
        sut.delete_values(data)
        self.assertEqual(data, [])

    def testDeleteValuesWithImmutable(self):
        data = [3]
        sut = ListSchema(self._item_schema)
        sut.mutable = False
        with self.assertRaises(NonDeletableValueError):
            sut.delete_values(data)

    def testDeleteValuesWithInvalidResult(self):
        data = [3]
        sut = ListSchema(self._item_schema, min_length=1)
        sut.mutable = True
        sut.assert_valid(data)
        with self.assertRaises(SchemaValueError):
            sut.delete_values(data)
        self.assertEqual(data, [3])


class DictSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._item_schemas = {
            'int': TypeSchema(int),
            'any': AnySchema(),
        }

    def testMutable(self):
        sut = DictSchema(self._item_schemas)
        self.assertFalse(sut.mutable)
        sut.mutable = True
        self.assertTrue(sut.mutable)

    def testSetValueWithMutable(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'any'
        value = 987654321
        sut = DictSchema(self._item_schemas)
        sut.mutable = True
        sut.set_value(data, key, value)
        self.assertEqual(data[key], value)

    def testSetValueWithImmutable(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'any'
        value = 987654321
        sut = DictSchema(self._item_schemas)
        sut.mutable = False
        with self.assertRaises(NonSettableValueError):
            sut.set_value(data, key, value)

    def testSetValueWithInvalidResult(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'int'
        value = '3'
        sut = DictSchema(self._item_schemas)
        sut.mutable = True
        with self.assertRaises(SchemaTypeError):
            sut.set_value(data, key, value)
        self.assertEqual(data, {
            'int': 3,
            'any': ('Foo', [], 987654321),
        })

    def testSetValueWithNonExistentSchemaKey(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        sut = DictSchema(self._item_schemas)
        sut.mutable = True
        with self.assertRaises(SchemaKeyError):
            sut.set_value(data, 'bar', 'Bar')

    def testDeleteValueWithMutable(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'any'
        sut = DictSchema(self._item_schemas, limit_required_keys=[])
        sut.mutable = True
        sut.delete_value(data, key)
        self.assertEqual(data, {
            'int': 3,
        })

    def testDeleteValueWithImmutable(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'any'
        sut = DictSchema(self._item_schemas)
        sut.mutable = False
        with self.assertRaises(NonDeletableValueError):
            sut.delete_value(data, key)

    def testDeleteValueWithInvalidResult(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'int'
        sut = DictSchema(self._item_schemas)
        sut.mutable = True
        with self.assertRaises(SchemaValueError):
            sut.delete_value(data, key)
        self.assertEqual(data, {
            'int': 3,
            'any': ('Foo', [], 987654321),
        })

    def testDeleteValueWithNonExistentSchemaKey(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        sut = DictSchema(self._item_schemas)
        sut.mutable = True
        with self.assertRaises(SchemaKeyError):
            sut.delete_value(data, 'bar')

    def testDeleteValuesWithMutable(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        sut = DictSchema(self._item_schemas, limit_required_keys=[])
        sut.mutable = True
        sut.delete_values(data)
        self.assertEqual(data, {})

    def testDeleteValuesWithImmutable(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        sut = DictSchema(self._item_schemas)
        sut.mutable = False
        with self.assertRaises(NonDeletableValueError):
            sut.delete_values(data)

    def testDeleteValuesWithInvalidResult(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        sut = DictSchema(self._item_schemas)
        sut.mutable = True
        with self.assertRaises(SchemaValueError):
            sut.delete_values(data)
        self.assertEqual(data, {
            'int': 3,
            'any': ('Foo', [], 987654321),
        })
