from alfred.app import Extension
from alfred_rest.extension import RestExtension
from alfred_rest.tests.extension.resource import RestTestResourceRepository


class RestTestExtension(Extension):
    @staticmethod
    def dependencies():
        return [RestExtension]

    @staticmethod
    def name():
        return 'rest-test'

    @Extension.service(tags=('resources',))
    def _resources(self):
        return RestTestResourceRepository()
