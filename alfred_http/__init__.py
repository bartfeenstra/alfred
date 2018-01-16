import base64
import os

from contracts import contract

RESOURCE_PATH = '/'.join((
    os.path.dirname(os.path.abspath(__file__)),
    'resources',
))


@contract
def base64_encodes(decoded: str) -> str:
    return base64.b64encode(bytes(decoded, 'utf-8')).decode('utf-8')


@contract
def base64_decodes(encoded: str) -> str:
    return base64.b64decode(encoded).decode('utf-8')
