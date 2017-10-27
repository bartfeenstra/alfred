from alfred.app import Extension
from alfred.factory import ClassFactory


class CoreExtension(Extension):
    @staticmethod
    def name():
        return 'core'

    def _class_factory(self) -> ClassFactory:
        return ClassFactory(self._app)

    def get_services(self):
        return {
            'factory': self._class_factory,
        }
