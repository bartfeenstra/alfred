from copy import deepcopy
from typing import Dict, Optional

from contracts import contract


class HttpBody:
    @contract
    def __init__(self, content: str, content_type: str):
        self._content = content
        self._content_type = content_type

    @property
    @contract
    def content(self) -> str:
        return self._content

    @property
    @contract
    def content_type(self) -> str:
        return self._content_type


class HttpRequest:
    def __init__(self, body: Optional[HttpBody] = None,
                 headers: Optional[Dict] = None,
                 arguments: Optional[Dict] = None):
        self._body = body
        # Copy the arguments to prevent the ones in this request from being
        # altered by calling code.
        self._arguments = {} if arguments is None else deepcopy(arguments)
        # Copy the headers to prevent the ones in this request from being
        # altered by calling code.
        self._headers = {} if headers is None else deepcopy(headers)

    @property
    def body(self) -> Optional[HttpBody]:
        return self._body

    @property
    @contract
    def headers(self) -> Dict:
        # Copy the headers to prevent the ones in this request from being
        # altered by calling code.
        return deepcopy(self._headers)

    @property
    @contract
    def arguments(self) -> Dict:
        # Copy the arguments to prevent the ones in this request from being
        # altered by calling code.
        return deepcopy(self._arguments)


class HttpResponse:
    def __init__(self, status: int, body: Optional[HttpBody] = None,
                 headers: Optional[Dict] = None):
        assert isinstance(status, int)
        assert body is None or isinstance(body, HttpBody)
        assert headers is None or isinstance(headers, Dict)
        self._status = status
        self._body = body
        # Copy the headers to prevent the ones in this request from being
        # altered by calling code.
        self._headers = {} if headers is None else deepcopy(headers)

    @property
    def body(self) -> Optional[HttpBody]:
        return self._body

    @property
    @contract
    def headers(self) -> Dict:
        # Copy the headers to prevent the ones in this request from being
        # altered by calling code.
        return deepcopy(self._headers)

    @property
    @contract
    def status(self) -> int:
        return self._status


class HttpResponseBuilder:
    def __init__(self):
        self._status = None
        self._body = None
        self._headers = {}

    @contract
    def to_response(self) -> HttpResponse:
        return HttpResponse(self.status, body=self.body, headers=self.headers)

    @property
    def body(self) -> Optional[HttpBody]:
        return self._body

    @body.setter
    def body(self, body: Optional[HttpBody]):
        assert body is None or isinstance(body, HttpBody)
        self._body = body

    @body.deleter
    def body(self):
        self._body = None

    @property
    @contract
    def headers(self) -> Dict:
        """
        Gets the HTTP response headers, mutable.
        :return: Dict
        """
        return self._headers

    @headers.setter
    @contract
    def headers(self, headers: Dict):
        assert isinstance(headers, Dict)
        self._headers = headers

    @property
    def status(self) -> Optional[int]:
        return self._status

    @status.setter
    def status(self, status: Optional[int]):
        assert status is None or isinstance(status, int)
        self._status = status
