import json as pythonjson
import os
from typing import Dict

from contracts import contract

RESOURCE_PATH = '/'.join((
    os.path.dirname(os.path.abspath(__file__)),
    'resources',
))


@contract
def json_schema() -> Dict:
    with open(RESOURCE_PATH + '/schemas/json-schema.json') as f:
        return pythonjson.load(f)
