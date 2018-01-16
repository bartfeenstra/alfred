from typing import Dict

from contracts import contract
from jsonschema import validate, RefResolver

from alfred_json.rewriter import Rewriter
from alfred_json.schema import SchemaProxy


class Validator:
    @contract
    def __init__(self, rewriter: Rewriter, schemas: SchemaProxy):
        self._rewriter = rewriter
        self._schemas = schemas

    @contract
    def validate(self, subject, schema: Dict):
        schema = self._rewriter.rewrite(schema)
        store = self._schemas.get_schemas()
        resolver = RefResolver.from_schema(schema, store=store)
        validate(subject, schema, resolver=resolver)
