from time import sleep
from typing import Optional, Dict

from contracts import contract

from alfred import indent, format_iter
from alfred.tests import expand_data, AppTestCase
from alfred_http.endpoints import Endpoint
from alfred_http.extension import HttpExtension
from alfred_http.http import HttpResponse, HttpBody


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


class HttpTestCase(AppTestCase):
    def setUp(self):
        super().setUp()
        flask_app = self._app.service('http', 'flask')
        self._flask_app = flask_app.test_client()
        self._flask_app_context = flask_app.app_context()
        self._flask_app_context.push()

    def get_extension_classes(self):
        return super().get_extension_classes() + [HttpExtension]

    def tearDown(self):
        super().tearDown()
        self._flask_app_context.pop()

    def request(self, endpoint_name: str, body: Optional[str] = None,
                parameters: Optional[Dict] = None,
                headers: Optional[Dict] = None) -> HttpResponse:
        urls = self._app.service('http', 'urls')
        url = urls.build(endpoint_name, parameters)
        endpoints = self._app.service('http', 'endpoints')
        endpoint = endpoints.get_endpoint(endpoint_name)
        assert isinstance(endpoint, Endpoint)
        # @todo Ensure we only pass query parameters to `requests`.
        response = None
        while response is None:
            try:
                response = getattr(self._flask_app,
                                   endpoint.request_type.method.lower())(url,
                                                                         data=body,
                                                                         query_string=parameters,
                                                                         headers=headers)
            except ConnectionRefusedError:
                # uWSGI can take a little long to boot, so allow it fo fail.
                sleep(1)
                continue

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
                '%s returned %s "%s" HTTP %d response, but it must either respond with an empty HTTP 4xx or 5xx response (empty body, and Content-Type and Content-Length headers), or one of the following content types:\n%s.' % (
                    url, empty, response.headers['Content-Type'],
                    response.status_code,
                    indent(format_iter(accepted_content_types))))

        return HttpResponse(response.status_code, HttpBody(response.get_data(as_text=True), response.headers['Content-Type']), dict(response.headers))

    @contract
    def assertResponseStatus(self, status: int, response: HttpResponse):
        # Allow statuses to be specified using their major digit only.
        if 0 > status < 10:
            self.assertEquals(str(response.status)[0], status)
        else:
            self.assertEquals(response.status, status)

    @contract
    def assertResponseContentType(self, content_type: str, response: HttpResponse):
        self.assertHeader('Content-Type', content_type, response)

    @contract
    def assertHeader(self, header: str, value: str, response):
        self.assertIn(header, response.headers)
        self.assertEquals(response.headers[header], value)
