from typing import List

from alfred_speech.schema import ensure_list
from alfred_speech.schema.tests import SchemaTestCase
from alfred_speech.schema.traverse import CoreTraverser, SchemaKeyError, \
    DictSchema, ListSchema, SchemaIndexError, RuntimeSchema, AndLikeSchema
from alfred_speech.schema.validate import SchemaTypeError, TypeSchema, \
    SchemaLookupError, AnySchema


class TypeSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._sut = TypeSchema(int)

    def testValidateWithIntValue(self):
        self.assertEquals(ensure_list(self._sut.validate(3)), [])

    def testValidateWithFloatValue(self):
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(self._sut.validate(3.0)))

    def testValidateWithStringValue(self):
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(self._sut.validate('3')))

    def testValidateWithIntListValue(self):
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(self._sut.validate([3])))

    def testIsValidWithIntValue(self):
        self.assertTrue(self._sut.is_valid(3))

    def testIsValidWithFloatValue(self):
        self.assertFalse(self._sut.is_valid(3.0))

    def testIsValidWithStringValue(self):
        self.assertFalse(self._sut.is_valid('3'))

    def testIsValidWithIntListValue(self):
        self.assertFalse(self._sut.is_valid([3]))

    def testAssertValidWithIntValue(self):
        self._sut.assert_valid(3)

    def testAssertValidWithFloatValue(self):
        with self.assertRaises(SchemaTypeError):
            self._sut.assert_valid(3.0)

    def testAssertValidWithStringValue(self):
        with self.assertRaises(SchemaTypeError):
            self._sut.assert_valid('3')

    def testAssertValidWithIntListValue(self):
        with self.assertRaises(SchemaTypeError):
            self._sut.assert_valid([3])


class ListSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._item_schema = TypeSchema(int)

    def testGetSchema(self):
        self.assertEqual(ListSchema(self._item_schema).get_schema(),
                         self._item_schema)

    def testGetValue(self):
        data = [3]
        value = 3
        self.assertEqual(ListSchema(self._item_schema).get_value(data, 0),
                         value)

    def testGetValues(self):
        value = [3, 1, 4]
        self.assertEqual(ListSchema(self._item_schema).get_values(value),
                         value)

    def testAssertValidSelectorWithValidValue(self):
        ListSchema(self._item_schema).assert_valid_selector(999)

    def testAssertValidSelectorWithInvalidValue(self):
        with self.assertRaises(SchemaIndexError):
            ListSchema(self._item_schema).assert_valid_selector('bar')


class DictSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._item_schemas = {
            'int': TypeSchema(int),
            'any': AnySchema(),
        }

    def testGetSchema(self):
        key = 'int'
        self.assertEqual(DictSchema(self._item_schemas).get_schema(key),
                         self._item_schemas[key])

    def testGetSchemas(self):
        self.assertEqual(DictSchema(self._item_schemas).get_schemas(),
                         self._item_schemas)

    def testAssertValidSelectorWithValidValue(self):
        DictSchema(self._item_schemas).assert_valid_selector('int')

    def testAssertValidSelectorWithInvalidValue(self):
        with self.assertRaises(SchemaKeyError):
            DictSchema(self._item_schemas).assert_valid_selector('bar')

    def testGetValue(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'any'
        self.assertEqual(DictSchema(self._item_schemas).get_value(data, key),
                         data[key])

    def testGetValueWithNonExistentSchemaKey(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        sut = DictSchema(self._item_schemas)
        with self.assertRaises(SchemaKeyError):
            sut.get_value(data, 'bar')

    def testGetValuse(self):
        data = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        key = 'any'
        self.assertEqual(DictSchema(self._item_schemas).get_values(data),
                         data)


class CoreTraverserTest(SchemaTestCase):
    def testAncestorsWithExhaustedPath(self):
        schema = TypeSchema(int)
        data = 3
        sut = CoreTraverser()
        self.assertEqual(sut.ancestors(schema, data, ()), [(schema, data, ())])

    def testAncestorsWithExhaustedSchema(self):
        schema = TypeSchema(int)
        data = 3
        sut = CoreTraverser()
        with self.assertRaises(SchemaLookupError):
            sut.ancestors(schema, data, ('foo',))

    def testAncestorsWithListLikeTraversableSchema(self):
        inner_schema = TypeSchema(int)
        inner_data = 3
        middle_schema = ListSchema(inner_schema)
        middle_data = [inner_data]
        schema = ListSchema(middle_schema)
        data = [middle_data]
        sut = CoreTraverser()
        self.assertEqual(sut.ancestors(schema, data, (0, 0)),
                         [(schema, data, ()),
                          (middle_schema, middle_data, (0,)),
                          (inner_schema, inner_data, (0, 0))])

    def testAncestorsWithDictLikeSchema(self):
        inner_schema = TypeSchema(int)
        inner_data = 3
        inner_selector = 'bar'
        middle_schema = DictSchema({
            inner_selector: inner_schema,
        })
        middle_data = {
            inner_selector: inner_data,
        }
        middle_selector = 'foo'
        schema = DictSchema({
            middle_selector: middle_schema,
        })
        data = {
            middle_selector: middle_data,
        }
        sut = CoreTraverser()
        self.assertEqual(sut.ancestors(schema, data, ('foo', 'bar')),
                         [(schema, data, ()),
                          (middle_schema, middle_data, ('foo',)),
                          (inner_schema, inner_data, ('foo', 'bar'))])

    def testAncestorsWithAndLikeSchema(self):
        class AndLikeSchemaDummy(AndLikeSchema):
            def __init__(self, schemas):
                self._schemas = schemas

            def validate(self, value):
                return []

            def get_schemas(self):
                return self._schemas

        inner_schema = TypeSchema(int)
        inner_data = 3
        middle_schema_one = TypeSchema(List)
        middle_schema_two = ListSchema(inner_schema)
        schema = AndLikeSchemaDummy([middle_schema_one, middle_schema_two])
        data = [inner_data]
        sut = CoreTraverser()
        self.assertEqual(sut.ancestors(schema, data, (0,)),
                         [(schema, data, ()),
                          (inner_schema, inner_data, (0,))])

    def testAncestorsWithRuntimeSchema(self):
        class RuntimeSchemaDummy(RuntimeSchema):
            def __init__(self, schema):
                self._schema = schema

            def get_schema(self, value):
                return self._schema

            def validate(self, value):
                return []

        inner_schema = TypeSchema(int)
        inner_data = 3
        middle_schema = ListSchema(inner_schema)
        middle_data = [inner_data]
        schema = RuntimeSchemaDummy(middle_schema)
        data = middle_data
        sut = CoreTraverser()
        self.assertEqual(sut.ancestors(schema, data, (0,)),
                         [(schema, data, ()),
                          (inner_schema, inner_data, (0,))])
