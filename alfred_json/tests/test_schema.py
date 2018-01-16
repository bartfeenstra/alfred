from alfred_json.schema import SchemaProxy, SchemaNotFound
from alfred_json.tests import JsonTestCase


class SchemaProxyTest(JsonTestCase):
    def testSchemaShouldFindExactMatch(self):
        schema_id = 'http://json-schema.org/draft-04/schema#'
        sut = SchemaProxy()
        self.assertEquals(sut.get_schema(schema_id)['id'], schema_id)

    def testSchemaShouldFindMatchWithRemovedFragment(self):
        schema_id = 'http://json-schema.org/draft-04/schema'
        sut = SchemaProxy()
        self.assertEquals(sut.get_schema(schema_id)['id'],
                          'http://json-schema.org/draft-04/schema#')

    def testSchemaShouldRaiseErrorForUnknownSchema(self):
        schema_id = 'https://example.com/schema#'
        sut = SchemaProxy()
        with self.assertRaises(SchemaNotFound):
            sut.get_schema(schema_id)

    def testGetSchemas(self):
        schema_id = 'http://json-schema.org/draft-04/schema#'
        sut = SchemaProxy()
        self.assertIn(schema_id, sut.get_schemas())
