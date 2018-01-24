from typing import Dict, Iterable, Optional

from contracts import contract, ContractsMeta, with_metaclass
from jsonschema.validators import validator_for

from alfred import format_iter
from alfred.app import App


class SchemaNotFound(RuntimeError):
    def __init__(self, schema_id: str,
                 available_schemas: Optional[Dict] = None):
        available_schemas = available_schemas if available_schemas is not None else {}
        if not available_schemas:
            message = 'Could not find schema "%s", because there are no schemas.' % schema_id
        else:
            message = 'Could not find schema "%s". Did you mean one of the following?\n' % schema_id + \
                      format_iter(available_schemas.keys())
        super().__init__(message)


class SchemaProxy(with_metaclass(ContractsMeta)):
    """
    Proxies JSON Schemas.

    JSON Schemas may require lazy-loading, because they are computed, for
    instance.
    """
    def __init__(self):
        self._schemas = None

    def get_schema(self, schema_id: str) -> Optional[Dict]:
        if self._schemas is None:
            self._aggregate_schemas()

        # Normalize root schemas by appending empty fragments.
        if '#' not in schema_id:
            schema_id += '#'
        try:
            return self._schemas[schema_id]
        except KeyError:
            raise SchemaNotFound(schema_id, self._schemas)

    @contract
    def get_schemas(self) -> Dict:
        if self._schemas is None:
            self._aggregate_schemas()

        return self._schemas

    def _aggregate_schemas(self):
        self._schemas = {}
        for schema in App.current.services(tag='json_schema'):
            self._add_schema(schema)

    @contract
    def _add_schema(self, schema: Dict):
        cls = validator_for(schema)
        cls.check_schema(schema)
        assert 'id' in schema
        # Normalize root schemas by appending empty fragments.
        if '#' not in schema['id']:
            schema['id'] += '#'
        assert schema['id'] not in self._schemas
        self._schemas[schema['id']] = schema
