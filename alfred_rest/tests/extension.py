from contracts import contract

from alfred.app import Extension, Factory
from alfred_http.endpoints import EndpointFactoryRepository, Endpoint, \
    ResponseMeta, RequestMeta, Request, Response
from alfred_rest.extension import RestExtension


class ProgrammedResponseRequest(Request):
    @contract
    def __init__(self, code: int):
        self.code = code


class ProgrammedResponseRequestMeta(RequestMeta):
    NAME = 'rest-test-programmed'

    def __init__(self):
        super().__init__(self.NAME, 'GET')

    def get_content_types(self):
        return ['*/*']

    def from_http_request(self, http_request, parameters):
        return ProgrammedResponseRequest(int(parameters['code']))


class ProgrammedResponse(Response):
    @contract
    def __init__(self, code: int):
        self._code = code

    def http_response_status_code(self):
        return self._code


class ProgrammedResponseMeta(ResponseMeta):
    NAME = 'rest-test-programmed'

    def __init__(self):
        super().__init__(self.NAME)

    def get_content_types(self):
        return ['*/*']


class ProgrammedResponseEndpoint(Endpoint):
    NAME = 'rest-test-programmed'

    @contract
    def __init__(self, factory: Factory):
        super().__init__(factory, self.NAME, '/rest-test/programmed/{code}',
                         ProgrammedResponseRequestMeta, ProgrammedResponseMeta)

    @classmethod
    def from_app(cls, app):
        return cls(app.factory)

    def handle(self, request):
        assert isinstance(request, ProgrammedResponseRequest)
        return ProgrammedResponse(request.code)


class RestTestExtension(Extension):
    @staticmethod
    def name():
        return 'rest-test'

    @staticmethod
    def dependencies():
        return [RestExtension]

    @Extension.service(tags=('http_endpoints',))
    def _endpoints(self):
        return EndpointFactoryRepository(self._app.factory, [
            ProgrammedResponseEndpoint,
        ])
