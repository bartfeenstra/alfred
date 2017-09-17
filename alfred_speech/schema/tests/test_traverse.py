from typing import List

from alfred_speech.schema.tests import SchemaTestCase
from alfred_speech.schema.traverse import CoreTraverser, SchemaKeyError, \
    DictSchema, ListSchema, SchemaIndexError, RuntimeSchema, CompositeSchema
from alfred_speech.schema.validate import TypeSchema, \
    SchemaLookupError, AnySchema


class CompositeSchemaTest(SchemaTestCase):
    class CompositeSchemaDummy(CompositeSchema):
        def __init__(self, schemas):
            self._schemas = schemas

        def validate(self, value):
            return []

        def get_schemas(self):
            return self._schemas

    class RuntimeSchemaDummy(RuntimeSchema):
        def __init__(self, schema):
            self._schema = schema

        def get_schema(self, value):
            return self._schema

    def testGetInstanceWithSelf(self):
        value = 7
        sut = self.CompositeSchemaDummy([TypeSchema(int)])
        self.assertEquals(sut.get_instance(value, self.CompositeSchemaDummy), sut)

    def testGetInstanceWithDecoratedSchemaInCorrectOrder(self):
        value = 7
        decorated_schema_one = TypeSchema(int)
        decorated_schema_two = TypeSchema(int)
        decorated_schema_three = TypeSchema(int)
        sut = self.CompositeSchemaDummy(
            [decorated_schema_one, decorated_schema_two,
             decorated_schema_three])
        self.assertEquals(sut.get_instance(value, TypeSchema), decorated_schema_one)

    def testGetInstanceWithDecoratedSchemaShouldIterate(self):
        value = 7
        found_schema = AnySchema()
        decorated_schema_one = TypeSchema(int)
        decorated_schema_two = self.CompositeSchemaDummy([])
        decorated_schema_three = self.CompositeSchemaDummy([found_schema])
        sut = self.CompositeSchemaDummy(
            [decorated_schema_one, decorated_schema_two,
             decorated_schema_three])
        self.assertEquals(sut.get_instance(value, AnySchema), found_schema)

    def testGetInstanceWithRuntimeSchema(self):
        value = 7
        inner_schema = TypeSchema(int)
        middle_schema = self.RuntimeSchemaDummy(inner_schema)
        outer_schema = self.RuntimeSchemaDummy(middle_schema)
        sut = self.CompositeSchemaDummy([outer_schema])
        self.assertEquals(sut.get_instance(value, TypeSchema), inner_schema)

    def testGetInstanceWithNone(self):
        value = 7
        decorated_schema_one = TypeSchema(float)
        decorated_schema_two = self.CompositeSchemaDummy(
            [TypeSchema(str), TypeSchema(object)])
        decorated_schema_three = self.RuntimeSchemaDummy(TypeSchema(int))
        sut = self.CompositeSchemaDummy(
            [decorated_schema_one, decorated_schema_two,
             decorated_schema_three])
        self.assertEquals(sut.get_instance(value, AnySchema), None)

    def testGetInstanceWithInvalidType(self):
        value = 7
        sut = self.CompositeSchemaDummy([])
        with self.assertRaises(ValueError):
            sut.get_instance(value, object)


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

    def testAncestorsWithCompositeSchema(self):
        class CompositeSchemaDummy(CompositeSchema):
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
        schema = CompositeSchemaDummy([middle_schema_one, middle_schema_two])
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
