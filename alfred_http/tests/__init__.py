from _signal import SIGINT
from typing import Optional, Dict
from unittest import TestCase

import os
import requests
import subprocess
from contracts import contract
from flask import Response as HttpResponse
from subprocess import Popen

from os.path import dirname

from alfred import indent, format_iter, qualname
from alfred.app import App
from alfred.tests import expand_data
from alfred_http.endpoints import Endpoint
from alfred_http.extension import HttpExtension


def provide_4xx_codes():
    """
    Returns the HTTP 4xx codes.
    See data_provider().
    """
    return expand_data(
        list(range(400, 418)) + list(range(421, 424)) + [426, 428, 429, 431,
                                                         451])


def provide_5xx_codes():
    """
    Returns the HTTP 5xx codes.
    See data_provider().
    """
    return expand_data(list(range(500, 508)) + [510, 511])


class HttpTestCase(TestCase):
    def setUp(self):
        extensions = self.get_extension_classes()

        # Set up a local copy of the app under test.
        self._app = App()
        for extension in extensions:
            self._app.add_extension(extension)
        self._flask_app = self._app.service('http', 'flask')
        self._flask_app_context = self._flask_app.app_context()
        self._flask_app_context.push()

        # Set up the app under test.
        uwsgi = ['uwsgi', '--http-socket', '0.0.0.0:5000', '-p', '2', '--manage-script-name', '--master', '--no-orphans', '--mount', '/=alfred_http.flask.entry_point:app']
        if extensions:
            uwsgi.append('--pyargv')
            uwsgi.append('%s' % ' '.join(map(qualname, extensions)))
        working_directory = dirname(dirname(dirname(os.path.realpath(__file__))))
        self._uwsgi = Popen(uwsgi, cwd=working_directory, stdout=subprocess.DEVNULL)

    def get_extension_classes(self):
        return [HttpExtension]

    def tearDown(self):
        self._flask_app_context.pop()
        self._uwsgi.send_signal(SIGINT)
        self._uwsgi.wait()

    def request(self, endpoint_name: str,
                parameters: Optional[Dict] = None,
                headers: Optional[Dict] = None) -> HttpResponse:
        urls = self._app.service('http', 'urls')
        url = urls.build(endpoint_name, parameters)
        endpoints = self._app.service('http', 'endpoints')
        endpoint = endpoints.get_endpoint(endpoint_name)
        assert isinstance(endpoint, Endpoint)
        # @todo Ensure we only pass query parameters to `requests`.
        response = getattr(requests, endpoint.request_meta.method.lower())(url,
                                                                           params=parameters,
                                                                           headers=headers)

        # Validate the content headers.
        accepted_content_types = []
        if headers is not None and 'Accept' in headers:
            for accept in headers['Accept'].split(','):
                if ';' in accept:
                    position = accept.index(';')
                    accept = accept[0:position]
                accepted_content_types.append(accept)
        accepted_content_types = [ct for ct in accepted_content_types if ct]
        if not (
                # The client accepts any response.
                not accepted_content_types or
                # An accepted success or error response.
                response.headers['Content-Type'] in accepted_content_types or
                # An empty error response.
                400 <= response.status_code < 600 and
                ('Content-Type' not in response.headers or
                 not response.headers['Content-Type']) and
                ('Content-Length' not in response.headers or
                 not int(response.headers['Content-Length']))
        ):
            empty = 'a non-empty' if len(response.text) > 0 else 'an empty'
            raise AssertionError(
                '%s returned %s "%s" HTTP %d response, but it must either respond with an empty HTTP 4xx or 5xx response, or one of the following content types:\n%s.' % (
                    url, empty, response.headers['Content-Type'],
                    response.status_code,
                    indent(format_iter(accepted_content_types))))

        return response

    @contract
    def assertResponseStatus(self, status: int, response):
        # Allow statuses to be specified using their major digit only.
        if 0 > status < 10:
            self.assertEquals(str(response.status_code)[0], status)
        else:
            self.assertEquals(response.status_code, status)

    @contract
    def assertResponseContentType(self, content_type: str, response):
        self.assertHeader('Content-Type', content_type, response)

    @contract
    def assertHeader(self, header: str, value: str, response):
        self.assertIn(header, response.headers)
        self.assertEquals(response.headers[header], value)
