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


class CoreMutatorTest(SchemaTestCase):
    # @todo
    # @todo This should also cover decorated schemas.
    # @todo Do we want OOP decoration? That gives decorators absolute control,
    # @todo but also requires them to extend all classes their children do.
    # @todo We can also use duck typing and magic decoration, but then we'd lose our type checks everywhere.
    # @todo Can we get a 'stack' per schema, so a list of all nested/decorated schemas?
    # @todo Then we can loop through them and find the first schema to be of the specified type.
    # @todo As with everything, such a stack depends on the data (RuntimeSchema)
    # @todo
    # @todo What if a stack contains CompositeSchema? That stack entry would have to have multiple values.
    # @todo The Mutator must be able to resolve those, even with decorators (in case CompositeSchema would be the top one)
    # @todo CompositeSchema returns schemas in order of decreasing priority, so Mutator
    # @todo can just check them in that order.
    # @todo
    # @todo
    # @todo
    # @todo
    # @todo Also ensure that when mutating values anywhere but at the top of a schema,
    # @todo the entire data structure is re-validated. It's easy on Mutators,
    # @todo because they receive the top-level schema and data, and then selectors
    # @todo to find the nested data. We can validate the entire data set from the top.
    # @todo However, this is done AFTER the data has already been mutated...
    # @todo Another common trick is to make schemas invoke their parent's validation.
    # @todo As parents also need to call their childrens' validators, we would need
    # @todo to find a way to prevent infinite loops. Drupal uses $notify?
    # @todo The problem with this is that the parent data is not available.
    # @todo
    # @todo What if we simplify the validation rules and just decide we don't support this crazy nonsense for now?
    # @todo For value objects it could be necessary, though. In that case, if there is a dependency between
    # @todo values of container objects, perhaps they should not be mutable.
    # @todo We want to introduce wizards/builders later anyway. They should solve this problem.
    # @todo
    # @todo


    # @todo
    # @todo With decorated schemas. If the topmost one must be used for validation
    # @todo (e.g. Nullable) and another one for setting, how do we set through
    # @todo the other one but validate through the top one?
    # @todo
    pass
