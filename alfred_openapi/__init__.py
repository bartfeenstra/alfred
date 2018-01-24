import json
import os
from typing import Dict

from contracts import contract

RESOURCE_PATH = '/'.join((
    os.path.dirname(os.path.abspath(__file__)),
    'resources',
))


@contract
def openapi_schema() -> Dict:
    with open(RESOURCE_PATH + '/schemas/openapi-2.0.json') as f:
        return json.load(f)
