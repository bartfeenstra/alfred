import json
from typing import Optional

import requests
from contracts import contract
from jsonschema import RefResolver, validate


class Json:
    def __init__(self, data):
        # Try dumping the data to ensure it is valid.
        json.dumps(data)
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


@contract
def get_schema(url: str) -> Json:
    """
    Gets a JSON Schema from a URL.
    :param url:
    :return:
    :raises HttpError
    """
    response = requests.get(url, headers={
        'Accept': 'application/schema+json; q=1, application/json; q=0.9, */*',
    })
    response.raise_for_status()
    return Json.from_raw(response.text)


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
            _, schema = reference_resolver.resolve(data['$schema'])
        else:
            schema = schema.data

        validate(data, schema, resolver=reference_resolver)
