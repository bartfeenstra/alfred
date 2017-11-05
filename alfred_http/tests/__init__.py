from typing import Optional, Dict
from unittest import TestCase

from alfred_http.flask.app import FlaskApp


class HttpTestCase(TestCase):
    def setUp(self):
        self._flask_app = FlaskApp(self.extension_classes)
        self._flask_app.config.update(SERVER_NAME='example.com')
        self._flask_app_context = self._flask_app.app_context()
        self._flask_app_context.push()
        self._flask_app_client = self._flask_app.test_client()
        self._app = self._flask_app.app

    @property
    def extension_classes(self):
        return []

    def tearDown(self):
        self._flask_app_context.pop()

    def request(self, endpoint_name: str, parameters: Optional[Dict] = None):
        if parameters is None:
            parameters = {}
        urls = self._app.service('http', 'urls')
        url = urls.build(endpoint_name, parameters)
        return self._flask_app_client.get(url)
