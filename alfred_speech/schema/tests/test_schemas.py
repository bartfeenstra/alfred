from alfred_speech.schema import ensure_list, SchemaError
from alfred_speech.schema.mutate import NonDeletableValueError, \
    NonSettableValueError
from alfred_speech.schema.schemas import EqualsSchema, \
    OrSchema, RangeSchema, AndSchema, NullableSchema, \
    IntrospectiveWhitelistSchema, ObjectAttributeSchema
from alfred_speech.schema.tests import SchemaTestCase
from alfred_speech.schema.validate import SchemaValueError, SchemaTypeError, \
    TypeSchema, AnySchema, SchemaAttributeError


class EqualsSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._invalid_values = [-9999999, 9999999, 999.999, 3.1, 4, None, '',
                                'Foo Bar', [],
                                ['Foo', 'Bar'], {}, (), ('Foo', 'Bar')]
        self._value = 3
        self._sut = EqualsSchema(self._value)

    def testValidateWithValidValue(self):
        self.assertEquals(ensure_list(self._sut.validate(self._value)), [])

    def testValidateWithInvalidValue(self):
        for value in self._invalid_values:
            self.assertContainsInstance(SchemaValueError,
                                        ensure_list(self._sut.validate(value)),
                                        'With value %s.' % str(value))

    def testIsValidWithValidValue(self):
        self.assertTrue(self._sut.is_valid(self._value))

    def testIsValidWithInvalidValue(self):
        for value in self._invalid_values:
            self.assertFalse(self._sut.is_valid(value),
                             'With value %s.' % str(value))

    def testAssertValidWithValidValue(self):
        self._sut.assert_valid(self._value)

    def testAssertValidWithInvalidValue(self):
        for value in self._invalid_values:
            with self.assertRaises(SchemaValueError):
                self._sut.assert_valid(value)


class NullableSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._nullable_type = TypeSchema(int)
        self._sut = NullableSchema(self._nullable_type)

    def testValidateWithInt(self):
        self.assertEquals(ensure_list(self._sut.validate(3)), [])

    def testValidateWithNone(self):
        self.assertEquals(ensure_list(self._sut.validate(None)), [])

    def testValidateWithInvalidValue(self):
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(self._sut.validate('Foo')))

    def testIsValidWithInt(self):
        self.assertTrue(self._sut.is_valid(3))

    def testIsValidWithNone(self):
        self.assertTrue(self._sut.is_valid(None))

    def testIsValidWithInvalidValue(self):
        self.assertFalse(self._sut.is_valid('Foo'))

    def testAssertValidWithInt(self):
        self._sut.assert_valid(3)

    def testAssertValidWithNone(self):
        self._sut.assert_valid(None)

    def testAssertValidWithInvalidValue(self):
        with self.assertRaises(SchemaValueError):
            self._sut.assert_valid('Foo')


class IntrospectiveWhitelistSchemaTest(SchemaTestCase):
    def setUp(self):
        super().setUp()

        self._whitelist = [('Foo', 'Foo'), (3, 'Three'), ([], 'The void')]
        self._blacklist = ['foo', 3.0000000001, 4, [None], {}]
        self._sut = IntrospectiveWhitelistSchema(self._whitelist)

    def testValidateWithValidValue(self):
        for value, _ in self._whitelist:
            self.assertEquals(ensure_list(self._sut.validate(value)), [],
                              'With value %s.' % str(value))

    def testValidateWithInvalidValue(self):
        for value in self._blacklist:
            self.assertContainsInstance(SchemaValueError,
                                        ensure_list(self._sut.validate(value)),
                                        'With value %s.' % str(value))

    def testIsValidWithValidValue(self):
        for value, _ in self._whitelist:
            self.assertTrue(self._sut.is_valid(value),
                            'With value %s.' % str(value))

    def testIsValidWithInvalidValue(self):
        for value in self._blacklist:
            self.assertFalse(self._sut.is_valid(value),
                             'With value %s.' % str(value))

    def testAssertValidWithValidValue(self):
        for value, _ in self._whitelist:
            self._sut.assert_valid(value)

    def testAssertValidWithInvalidValue(self):
        for value in self._blacklist:
            with self.assertRaises(SchemaValueError,
                                   msg='With value %s.' % str(value)):
                self._sut.assert_valid(value)

    def testEnum(self):
        self.assertEqual(self._sut.enum, self._whitelist)


class RangeSchemaTest(SchemaTestCase):
    def testValidateWithoutMinimum(self):
        self.assertEquals(ensure_list(RangeSchema().validate(-3)), [])

    def testValidateWithValueAboveMinimum(self):
        self.assertEquals(ensure_list(RangeSchema(0).validate(3)), [])

    def testValidateWithValueBelowMinimum(self):
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(RangeSchema(0).validate(-3)))

    def testValidateWithoutMaximum(self):
        self.assertEquals(ensure_list(RangeSchema().validate(3)), [])

    def testValidateWithValueAboveMaximum(self):
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(
                                        RangeSchema(max=0).validate(3)))

    def testValidateWithValueBelowMaximum(self):
        self.assertEquals(ensure_list(RangeSchema(max=0).validate(-3)), [])

    def testIsValidWithoutMinimum(self):
        self.assertTrue(RangeSchema().is_valid(-3))

    def testIsValidWithValueAboveMinimum(self):
        self.assertTrue(RangeSchema(0).is_valid(3))

    def testIsValidWithValueBelowMinimum(self):
        self.assertFalse(RangeSchema(0).is_valid(-3))

    def testIsValidWithoutMaximum(self):
        self.assertTrue(RangeSchema().is_valid(3))

    def testIsValidWithValueAboveMaximum(self):
        self.assertFalse(RangeSchema(max=0).is_valid(3))

    def testIsValidWithValueBelowMaximum(self):
        self.assertTrue(RangeSchema(max=0).is_valid(-3))

    def testAssertValidWithoutMinimum(self):
        RangeSchema().assert_valid(-3)

    def testAssertValidWithValueAboveMinimum(self):
        RangeSchema(0).assert_valid(3)

    def testAssertValidWithValueBelowMinimum(self):
        with self.assertRaises(SchemaValueError):
            RangeSchema(0).assert_valid(-3)

    def testAssertValidWithoutMaximum(self):
        RangeSchema().assert_valid(3)

    def testAssertValidWithValueAboveMaximum(self):
        with self.assertRaises(SchemaValueError):
            RangeSchema(max=0).assert_valid(3)

    def testAssertValidWithValueBelowMaximum(self):
        RangeSchema(max=0).assert_valid(-3)


class AndSchemaTest(SchemaTestCase):
    def testValidateWithNoneValid(self):
        sut = AndSchema(
            [self.AlwaysInvalidSchema(), self.AlwaysInvalidSchema()])
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(sut.validate(3)))

    def testValidateWithSomeValid(self):
        sut = AndSchema([AnySchema(), self.AlwaysInvalidSchema()])
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(sut.validate(3)))

    def testValidateWithAllValid(self):
        sut = AndSchema([AnySchema(), AnySchema()])
        self.assertEquals(ensure_list(sut.validate(3)), [])

    def testIsValidWithWithNoneValid(self):
        sut = AndSchema(
            [self.AlwaysInvalidSchema(), self.AlwaysInvalidSchema()])
        self.assertFalse(sut.is_valid(3))

    def testIsValidWithWithSomeValid(self):
        sut = AndSchema([AnySchema(), self.AlwaysInvalidSchema()])
        self.assertFalse(sut.is_valid(3))

    def testIsValidWithWithAllValid(self):
        sut = AndSchema([AnySchema(), AnySchema()])
        self.assertTrue(sut.is_valid(3))

    def testAssertValidWithNoneValid(self):
        sut = AndSchema(
            [self.AlwaysInvalidSchema(), self.AlwaysInvalidSchema()])
        with self.assertRaises(SchemaError):
            sut.assert_valid(3)

    def testAssertValidWithSomeValid(self):
        sut = AndSchema([AnySchema(), self.AlwaysInvalidSchema()])
        with self.assertRaises(SchemaError):
            sut.assert_valid(3)

    def testAssertValidWithAllValid(self):
        sut = AndSchema([AnySchema(), AnySchema()])
        sut.assert_valid(3)


class OrSchemaTest(SchemaTestCase):
    def testValidateWithNoneValid(self):
        sut = OrSchema(
            [self.AlwaysInvalidSchema(), self.AlwaysInvalidSchema()])
        self.assertContainsInstance(SchemaValueError,
                                    ensure_list(sut.validate(3)))

    def testValidateWithSomeValid(self):
        sut = OrSchema([AnySchema(), self.AlwaysInvalidSchema()])
        self.assertEquals(ensure_list(sut.validate(3)), [])

    def testValidateWithAllValid(self):
        sut = OrSchema([AnySchema(), AnySchema()])
        self.assertEquals(ensure_list(sut.validate(3)), [])

    def testIsValidWithWithNoneValid(self):
        sut = OrSchema(
            [self.AlwaysInvalidSchema(), self.AlwaysInvalidSchema()])
        self.assertFalse(sut.is_valid(3))

    def testIsValidWithWithSomeValid(self):
        sut = OrSchema([AnySchema(), self.AlwaysInvalidSchema()])
        self.assertTrue(sut.is_valid(3))

    def testIsValidWithWithAllValid(self):
        sut = OrSchema([AnySchema(), AnySchema()])
        self.assertTrue(sut.is_valid(3))

    def testAssertValidWithNoneValid(self):
        sut = OrSchema(
            [self.AlwaysInvalidSchema(), self.AlwaysInvalidSchema()])
        with self.assertRaises(SchemaError):
            sut.assert_valid(3)

    def testAssertValidWithSomeValid(self):
        sut = OrSchema([AnySchema(), self.AlwaysInvalidSchema()])
        sut.assert_valid(3)

    def testAssertValidWithAllValid(self):
        sut = OrSchema([AnySchema(), AnySchema()])
        sut.assert_valid(3)


class ObjectAttributeSchemaTest(SchemaTestCase):
    class Sut(object):
        def __init__(self):
            self._foo = None
            self._bar = None

        @property
        def foo(self):
            return self._foo

        @foo.setter
        def foo(self, foo):
            self._foo = foo

        @foo.deleter
        def foo(self):
            self._foo = None

    def setUp(self):
        super().setUp()

        self._attribute_schemas = {
            'foo': NullableSchema(TypeSchema(str)),
        }
        self._sut = ObjectAttributeSchema(self.Sut, self._attribute_schemas)

    def testValidateWithValidValue(self):
        value = self.Sut()
        self.assertEqual(ensure_list(self._sut.validate(value)), [])

    def testValidateWithInvalidType(self):
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(self._sut.validate({})))

    def testValidateWithInvalidItemType(self):
        value = self.Sut()
        value.foo = 3
        self.assertContainsInstance(SchemaTypeError,
                                    ensure_list(self._sut.validate(value)))

    def testIsValidWithValidValue(self):
        value = self.Sut()
        self.assertTrue(self._sut.is_valid(value))

    def testIsValidWithInvalidType(self):
        self.assertFalse(self._sut.is_valid({}))

    def testIsValidWithInvalidItemType(self):
        value = self.Sut()
        value.foo = 3
        self.assertFalse(self._sut.is_valid(value))

    def testAssertValidWithValidValue(self):
        value = self.Sut()
        self._sut.assert_valid(value)

    def testAssertValidWithInvalidType(self):
        with self.assertRaises(SchemaTypeError):
            self._sut.assert_valid({})

    def testAssertValidWithInvalidItemType(self):
        value = self.Sut()
        value.foo = 9
        with self.assertRaises(SchemaError):
            self._sut.assert_valid(value)

    def testGetSchema(self):
        attribute = 'foo'
        self.assertEqual(self._sut.get_schema(attribute),
                         self._attribute_schemas[attribute])

    def testGetSchemas(self):
        self.assertEqual(self._sut.get_schemas(),
                         self._attribute_schemas)

    def testAssertValidSelectorWithValidValue(self):
        self._sut.assert_valid_selector('foo')

    def testAssertValidSelectorWithInvalidValue(self):
        with self.assertRaises(SchemaAttributeError):
            self._sut.assert_valid_selector('bar')

    def testMutable(self):
        self.assertFalse(self._sut.mutable)
        self._sut.mutable = True
        self.assertTrue(self._sut.mutable)

    def testGetValue(self):
        data = self.Sut()
        value = 'Foo'
        data.foo = value
        self.assertEqual(self._sut.get_value(data, 'foo'), value)

    def testGetValueWithNonExistentSchemaKey(self):
        data = self.Sut()
        with self.assertRaises(SchemaAttributeError):
            self._sut.get_value(data, 'bar')

    def testSetValueWithMutable(self):
        data = self.Sut()
        value = 'Foo'
        self._sut.mutable = True
        self._sut.set_value(data, 'foo', value)
        self.assertEqual(data.foo, value)

    def testSetValueWithImmutable(self):
        data = self.Sut()
        value = 'Foo'
        self._sut.mutable = False
        with self.assertRaises(NonSettableValueError):
            self._sut.set_value(data, 'foo', value)
        self.assertEqual(data.__dict__, self.Sut().__dict__)

    def testSetValueWithInvalidResult(self):
        data = self.Sut()
        value = 3
        self._sut.mutable = True
        with self.assertRaises(SchemaError):
            self._sut.set_value(data, 'foo', value)
        self.assertEqual(data.__dict__, self.Sut().__dict__)

    def testSetValueWithNonExistentSchemaKey(self):
        data = self.Sut()
        self._sut.mutable = True
        with self.assertRaises(SchemaAttributeError):
            self._sut.set_value(data, 'bar', 'Bar')

    def testDeleteValueWithMutable(self):
        data = self.Sut()
        value = 'Foo'
        data.foo = value
        self._sut.mutable = True
        self._sut.delete_value(data, 'foo')
        self.assertIsNone(data.foo)

    def testDeleteValueWithImmutable(self):
        data = self.Sut()
        value = 'Foo'
        data.foo = value
        self._sut.mutable = False
        with self.assertRaises(NonDeletableValueError):
            self._sut.delete_value(data, 'foo')
        self.assertEqual(data.foo, value)

    def testDeleteValueWithInvalidResult(self):
        data = self.Sut()
        sut = ObjectAttributeSchema(self.Sut, {
            'foo': TypeSchema(str),
        })
        sut.mutable = True
        with self.assertRaises(SchemaTypeError):
            sut.delete_value(data, 'foo')
        self.assertEqual(data.__dict__, self.Sut().__dict__)

    def testDeleteValueWithNonExistentSchemaKey(self):
        data = self.Sut()
        self._sut.mutable = True
        with self.assertRaises(SchemaAttributeError):
            self._sut.delete_value(data, 'bar')
