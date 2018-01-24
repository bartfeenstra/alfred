from alfred.app import Extension, App
from alfred_json import json_schema
from alfred_json.rewriter import NestedRewriter, IdentifiableDataTypeAggregator
from alfred_json.schema import SchemaProxy
from alfred_json.validator import Validator


class JsonExtension(Extension):
    @staticmethod
    def name():
        return 'json'

    @staticmethod
    def dependencies():
        return []

    @Extension.service()
    def _validator(self) -> Validator:
        return Validator(App.current.service('json', 'schema_rewriter'), App.current.service('json', 'schemas'))

    @Extension.service()
    def _schema_rewriter(self):
        rewriter = NestedRewriter()
        for tagged_rewriter in App.current.services(
                tag='json_schema_rewriter'):
            rewriter.add_rewriter(tagged_rewriter)
        return rewriter

    @Extension.service(tags=('json_schema_rewriter',))
    def _identifiable_data_type_aggregator(self):
        return IdentifiableDataTypeAggregator()

    @Extension.service()
    def _schemas(self):
        return SchemaProxy()

    @Extension.service(tags=('json_schema',))
    def _json_schema(self):
        return json_schema()
