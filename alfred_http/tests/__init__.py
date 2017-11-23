from typing import Optional, Dict
from unittest import TestCase

import requests
from contracts import contract
from flask import Response as HttpResponse

from alfred.app import App
from alfred_http.endpoints import Endpoint
from alfred_http.extension import HttpExtension


class HttpTestCase(TestCase):
    def setUp(self):
        self._app = App()
        for extension in self.get_extension_classes():
            self._app.add_extension(extension)
        self._flask_app = self._app.service('http', 'flask')
        self._flask_app_context = self._flask_app.app_context()
        self._flask_app_context.push()

    def get_extension_classes(self):
        return [HttpExtension]

    def tearDown(self):
        self._flask_app_context.pop()

    def request(self, endpoint_name: str,
                parameters: Optional[Dict] = None, headers: Optional[Dict]=None) -> HttpResponse:
        urls = self._app.service('http', 'urls')
        url = urls.build(endpoint_name, parameters)
        endpoints = self._app.service('http', 'endpoints')
        endpoint = endpoints.get_endpoint(endpoint_name)
        assert isinstance(endpoint, Endpoint)
        # @todo Ensure we only pass query parameters to `requests`.
        return getattr(requests, endpoint.request_meta.method.lower())(url, params=parameters, headers=headers)

    @contract
    def assertResponseStatus(self, status: int, response):
        # Allow statuses to be specified using their major digit only.
        if 0 > status < 10:
            self.assertEquals(str(response.status_code)[0], status)
        else:
            self.assertEquals(response.status_code, 200)

    @contract
    def assertResponseContentType(self, content_type: str, response):
        self.assertHeader('Content-Type', content_type, response)

    @contract
    def assertHeader(self, header: str, value: str, response):
        self.assertIn(header, response.headers)
        self.assertEquals(response.headers[header], value)
