import json
from typing import Optional

import requests
from jsonschema import RefResolver, validate


class Json:
    def __init__(self, data):
        self._data = data

    @classmethod
    def from_raw(cls, raw: str) -> 'Json':
        return cls(json.loads(raw))

    @classmethod
    def from_data(cls, data) -> 'Json':
        return cls(data)

    @property
    def raw(self) -> str:
        return json.dumps(self.data)

    @property
    def data(self):
        return self._data


class Validator:
    def validate(self, subject: Json, schema: Optional[Json] = None):
        reference_resolver = RefResolver(
            'http://localhost', 'http://localhost')
        data = subject.data
        if schema is None:
            message = 'The JSON must be an object with a "schema" key.'
            if not isinstance(data, dict):
                raise ValueError('The JSON is not an object: %s' % message)
            if '$schema' not in data:
                raise KeyError('No "$schema" key found: %s' % message)
            schema = requests.get(data['$schema'], headers={
                'Accept': 'application/schema+json; q=1, application/json; q=0.9, */*',
            }).json()
        else:
            schema = schema.data

        validate(data, schema, resolver=reference_resolver)
