from jsonschema import ValidationError

from alfred_json.rewriter import Rewriter
from alfred_json.schema import SchemaProxy
from alfred_json.tests import JsonTestCase
from alfred_json.validator import Validator

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


class ValidatorTest(JsonTestCase):
    class PassThroughRewriter(Rewriter):
        def rewrite(self, schema):
            return schema

    def testValidate(self):
        validator = Validator(self.PassThroughRewriter(), SchemaProxy())
        data = {
            'fruit_name': 'Apple',
        }
        validator.validate(data, SCHEMA)

    def testValidateWithFailure(self):
        validator = Validator(self.PassThroughRewriter(), SchemaProxy())
        data = {}
        with self.assertRaises(ValidationError):
            validator.validate(data, SCHEMA)
