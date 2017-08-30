from alfred_speech.schema import ensure_list
from alfred_speech.schema.tests import SchemaTestCase
from alfred_speech.schema.validate import AnySchema, TypeSchema, \
    SchemaTypeError, SchemaValueError, ListSchema, DictSchema


class AnySchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._sut = AnySchema()
        self._values = [-9999999, 9999999, 999.999, None, '', 'Foo Bar', [],
                        ['Foo', 'Bar'], {}, (), ('Foo', 'Bar')]

    def testValidate(self):
        for value in self._values:
            self.assertEquals(ensure_list(self._sut.validate(value)), [],
                              'With value %s.' % str(value))

    def testIsValid(self):
        for value in self._values:
            self.assertTrue(self._sut.is_valid(value),
                            'With value %s.' % str(value))

    def testAssertValid(self):
        for value in self._values:
            self._sut.assert_valid(value)


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

    def testValidateWithValidValue(self):
        sut = ListSchema(self._item_schema)
        self.assertEqual(ensure_list(sut.validate([3])), [])

    def testValidateWithInvalidType(self):
        sut = ListSchema(self._item_schema)
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(sut.validate(3)))

    def testValidateWithInvalidItemType(self):
        sut = ListSchema(self._item_schema)
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(sut.validate(['3'])))

    def testValidateWithValidMinimumLength(self):
        sut = ListSchema(self._item_schema, 1)
        self.assertEqual(ensure_list(sut.validate([3])), [])

    def testValidateWithInvalidMinimumLength(self):
        sut = ListSchema(self._item_schema, 1)
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(sut.validate([])))

    def testValidateWithValidMaximumLength(self):
        sut = ListSchema(self._item_schema, max_length=1)
        self.assertEqual(ensure_list(sut.validate([])), [])

    def testValidateWithInvalidMaximumLength(self):
        sut = ListSchema(self._item_schema, max_length=1)
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(sut.validate([3, 3])))

    def testIsValidWithValidValue(self):
        sut = ListSchema(self._item_schema)
        self.assertTrue(sut.is_valid([3]))

    def testIsValidWithInvalidType(self):
        sut = ListSchema(self._item_schema)
        self.assertFalse(sut.is_valid(3))

    def testIsValidWithInvalidItemType(self):
        sut = ListSchema(self._item_schema)
        self.assertFalse(sut.is_valid(['3']))

    def testIsValidWithValidMinimumLength(self):
        sut = ListSchema(self._item_schema, 1)
        self.assertTrue(sut.is_valid([3]))

    def testIsValidWithInvalidMinimumLength(self):
        sut = ListSchema(self._item_schema, 1)
        self.assertFalse(sut.is_valid([]))

    def testIsValidWithValidMaximumLength(self):
        sut = ListSchema(self._item_schema, max_length=1)
        self.assertTrue(sut.is_valid([]))

    def testIsValidWithInvalidMaximumLength(self):
        sut = ListSchema(self._item_schema, max_length=1)
        self.assertFalse(sut.is_valid([3, 3]))

    def testAssertValidWithValidValue(self):
        sut = ListSchema(self._item_schema)
        sut.assert_valid([3])

    def testAssertValidWithInvalidType(self):
        sut = ListSchema(self._item_schema)
        with self.assertRaises(SchemaTypeError):
            sut.assert_valid(3)

    def testAssertValidWithInvalidItemType(self):
        sut = ListSchema(self._item_schema)
        with self.assertRaises(SchemaTypeError):
            sut.assert_valid(['3'])

    def testAssertValidWithValidMinimumLength(self):
        sut = ListSchema(self._item_schema, 1)
        sut.assert_valid([3])

    def testAssertValidWithInvalidMinimumLength(self):
        sut = ListSchema(self._item_schema, 1)
        with self.assertRaises(SchemaValueError):
            sut.assert_valid([])

    def testAssertValidWithValidMaximumLength(self):
        sut = ListSchema(self._item_schema, max_length=1)
        sut.assert_valid([])

    def testAssertValidWithInvalidMaximumLength(self):
        sut = ListSchema(self._item_schema, max_length=1)
        with self.assertRaises(SchemaValueError):
            sut.assert_valid([3, 3])


class DictSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._item_schemas = {
            'int': TypeSchema(int),
            'any': AnySchema(),
        }

    def testValidateWithValidValue(self):
        sut = DictSchema(self._item_schemas)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        self.assertEqual(ensure_list(sut.validate(value)), [])

    def testValidateWithInvalidType(self):
        sut = DictSchema(self._item_schemas)
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(sut.validate(3)))

    def testValidateWithInvalidItemType(self):
        sut = DictSchema(self._item_schemas)
        value = {
            'int': '3',
            'any': ('Foo', [], 987654321),
        }
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(sut.validate(value)))

    def testValidateWithAllowedAdditionalKey(self):
        sut = DictSchema(self._item_schemas, allow_additional_keys=True)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
            'foo': 'Bar',
        }
        self.assertEqual(ensure_list(sut.validate(value)), [])

    def testValidateWithDisallowedAdditionalKey(self):
        sut = DictSchema(self._item_schemas, allow_additional_keys=False)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
            'foo': 'Bar',
        }
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(sut.validate(value)))

    def testValidateWithMissingRequiredKey(self):
        sut = DictSchema(self._item_schemas, limit_required_keys=['any'])
        value = {
            'int': 3,
        }
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(sut.validate(value)))

    def testIsValidWithValidValue(self):
        sut = DictSchema(self._item_schemas)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        self.assertTrue(sut.is_valid(value))

    def testIsValidWithInvalidType(self):
        sut = DictSchema(self._item_schemas)
        self.assertFalse(sut.is_valid(3))

    def testIsValidWithInvalidItemType(self):
        sut = DictSchema(self._item_schemas)
        value = {
            'int': '3',
            'any': ('Foo', [], 987654321),
        }
        self.assertFalse(sut.is_valid(value))

    def testIsValidWithAllowedAdditionalKey(self):
        sut = DictSchema(self._item_schemas, allow_additional_keys=True)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
            'foo': 'Bar',
        }
        self.assertTrue(sut.is_valid(value))

    def testIsValidWithDisallowedAdditionalKey(self):
        sut = DictSchema(self._item_schemas, allow_additional_keys=False)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
            'foo': 'Bar',
        }
        self.assertFalse(sut.is_valid(value))

    def testIsValidWithMissingRequiredKey(self):
        sut = DictSchema(self._item_schemas, limit_required_keys=['any'])
        value = {
            'int': 3,
        }
        self.assertFalse(sut.is_valid(value))

    def testAssertValidWithValidValue(self):
        sut = DictSchema(self._item_schemas)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
        }
        sut.assert_valid(value)

    def testAssertValidWithInvalidType(self):
        sut = DictSchema(self._item_schemas)
        with self.assertRaises(SchemaTypeError):
            sut.assert_valid(3)

    def testAssertValidWithInvalidItemType(self):
        sut = DictSchema(self._item_schemas)
        value = {
            'int': '3',
            'any': ('Foo', [], 987654321),
        }
        with self.assertRaises(SchemaTypeError):
            sut.assert_valid(value)

    def testAssertValidWithAllowedAdditionalKey(self):
        sut = DictSchema(self._item_schemas, allow_additional_keys=True)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
            'foo': 'Bar',
        }
        sut.assert_valid(value)

    def testAssertValidWithDisallowedAdditionalKey(self):
        sut = DictSchema(self._item_schemas, allow_additional_keys=False)
        value = {
            'int': 3,
            'any': ('Foo', [], 987654321),
            'foo': 'Bar',
        }
        with self.assertRaises(SchemaValueError):
            sut.assert_valid(value)

    def testAssertValidWithMissingRequiredKey(self):
        sut = DictSchema(self._item_schemas, limit_required_keys=['any'])
        value = {
            'int': 3,
        }
        with self.assertRaises(SchemaValueError):
            sut.assert_valid(value)
